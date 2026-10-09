#!/usr/bin/env python3
"""Homelab-owned bounded local archive and automation verification."""

import argparse
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
from threading import Thread
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
PHASES = ("automation_check", "automation_idempotence", "restore", "schema",
          "integrity", "synthetic")


class VerificationFailure(Exception):
    def __init__(self, reason, state="failed", artifact_sha256=None):
        self.reason = reason
        self.state = state
        self.artifact_sha256 = artifact_sha256


class VerificationInterrupted(BaseException):
    """Terminate execution immediately so timeout cannot launch another phase."""


def command(argv, workspace, timeout=30):
    """Bound process groups/output and discard all raw diagnostics."""
    env = {"PATH": os.environ.get("PATH", os.defpath), "LANG": "C.UTF-8",
           "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(workspace),
           "ANSIBLE_CONFIG": str(ROOT / "recovery/ansible.cfg"),
           "ANSIBLE_NOCOLOR": "1"}
    try:
        with subprocess.Popen(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, start_new_session=True) as process:
            output = bytearray()
            deadline = monotonic() + timeout
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stdout, selectors.EVENT_READ)
                    while True:
                        remaining = deadline - monotonic()
                        if remaining <= 0 or not selector.select(remaining):
                            raise VerificationFailure("command_timeout", "unavailable")
                        chunk = os.read(process.stdout.fileno(), 4096)
                        if not chunk:
                            break
                        output.extend(chunk)
                        if len(output) > 65536:
                            raise VerificationFailure("output_limit_exceeded")
                process.wait(timeout=max(0, deadline - monotonic()))
                if process.returncode:
                    raise VerificationFailure("command_failed")
                return bytes(output)
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=10)
    except FileNotFoundError:
        raise VerificationFailure("tool_unavailable", "unavailable") from None
    except subprocess.TimeoutExpired:
        raise VerificationFailure("command_timeout", "unavailable") from None


def observation(phase, state, reason, digest=None):
    result = {"id": phase, "phase": phase, "state": state, "reason": reason}
    if digest is not None:
        result["artifact_sha256"] = digest
    return result


def record(checks, phase, action):
    try:
        digest = action()
    except VerificationFailure as error:
        checks.append(observation(phase, error.state, error.reason, error.artifact_sha256))
        return False
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError):
        checks.append(observation(phase, "failed", "invalid_recovery_input"))
        return False
    checks.append(observation(phase, "passed", "verified", digest))
    return True


def approved_automation(workspace, check_mode=False):
    policy = json.loads((ROOT / "recovery/weekly-policy.json").read_text())
    # Only the reviewed local playbook can be applied. No arbitrary playbook,
    # inventory, tags, extra-vars or production connection settings are accepted.
    if policy["idempotence_safe"] is not True:
        raise VerificationFailure("idempotence_not_approved")
    args = ["ansible-playbook", "-i", "localhost,", "-c", "local",
            "recovery/weekly.yml", "-e", json.dumps({"recovery_workspace": str(workspace)})]
    if check_mode:
        args.append("--check")
    output = command(args, workspace, 45)
    recaps = re.findall(rb"localhost\s*:\s*ok=(\d+)\s+changed=(\d+)\s+unreachable=(\d+)\s+failed=(\d+)\s+skipped=(\d+)", output)
    if len(recaps) != 1 or int(recaps[0][2]) or int(recaps[0][3]):
        raise VerificationFailure("invalid_ansible_recap")
    if check_mode and int(recaps[0][4]):
        raise VerificationFailure("unsupported_check_mode_task")
    return int(recaps[0][1])


def automation(checks, workspace):
    record(checks, "automation_check", lambda: check_automation(workspace))
    record(checks, "automation_idempotence", lambda: idempotence(workspace))
    for task, reason in json.loads((ROOT / "recovery/weekly-policy.json").read_text())["check_mode_exclusions"].items():
        checks.append({"id": task, "phase": "classification",
                       "state": "not_applicable", "reason": reason})


def check_automation(workspace):
    approved_automation(workspace, check_mode=True)


def idempotence(workspace):
    policy = json.loads((ROOT / "recovery/weekly-policy.json").read_text())
    approved_automation(workspace)
    changes = approved_automation(workspace)
    # Reviewed aggregate allowance, zero by default. No inferred task exceptions.
    if changes > policy["allowed_second_run_changes"]:
        raise VerificationFailure("idempotence_drift")


def digest_file(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16 * 1024 * 1024:
        raise VerificationFailure("backup_unreadable")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def restore_archive(checks, workspace):
    policy = json.loads((ROOT / "recovery/weekly-policy.json").read_text())
    backup = ROOT / "recovery/fixtures/representative.tar"
    destination = workspace / "restored"
    destination.mkdir(mode=0o700)
    def restore():
        digest = digest_file(backup)
        if digest != policy["backup_sha256"]:
            raise VerificationFailure("backup_checksum_mismatch", artifact_sha256=digest)
        with tarfile.open(backup, "r:") as archive:
            members = archive.getmembers()
            if len(members) > 32 or sum(member.size for member in members) > 1024 * 1024:
                raise VerificationFailure("archive_limit_exceeded")
            # Only regular declared files, no links/devices/traversal/overwrites.
            if (len({member.name for member in members}) != len(members)
                    or {member.name for member in members} != set(policy["files"])):
                raise VerificationFailure("archive_schema_mismatch")
            for member in members:
                path = destination / member.name
                if not member.isfile() or not path.resolve().is_relative_to(destination.resolve()):
                    raise VerificationFailure("unsafe_archive_member")
            archive.extractall(destination, filter="data")
        return digest

    def schema():
        if {path.name for path in destination.iterdir()} != set(policy["files"]):
            raise VerificationFailure("restored_schema_mismatch")

    def integrity():
        for name, digest in policy["files"].items():
            if digest_file(destination / name) != digest:
                raise VerificationFailure("restored_integrity_mismatch")

    def synthetic():
        command(["bash", "-n", str(workspace / "wait-for-media.sh")], workspace)
        config = json.loads((destination / "routes.json").read_text())
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                route = config["routes"].get(self.path, {"status": 404, "body": None})
                self.send_response(route["status"])
                self.end_headers()
                self.wfile.write(json.dumps(route["body"]).encode())

            def log_message(self, format, *args):
                pass  # Never record restored data or request contents.

        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for route, expected in (("/healthz", "ok"),
                                        ("/library", {"items": ["recovery-fixture"], "count": 1})):
                    connection = http.client.HTTPConnection(*server.server_address, timeout=2)
                    try:
                        connection.request("GET", route)
                        response = connection.getresponse()
                        if response.status != 200 or json.loads(response.read(4096)) != expected:
                            raise VerificationFailure("restored_service_unusable")
                    finally:
                        connection.close()
            finally:
                server.shutdown()
                thread.join(timeout=2)
                if thread.is_alive():
                    raise VerificationFailure("temporary_service_cleanup_failed")

    if record(checks, "restore", restore):
        record(checks, "schema", schema)
        record(checks, "integrity", integrity)
        record(checks, "synthetic", synthetic)
    else:
        for phase in ("schema", "integrity", "synthetic"):
            checks.append(observation(phase, "skipped", "restore_not_completed"))


def verify(deadline_seconds=240):
    checks = []
    try:
        workspace = Path(tempfile.mkdtemp(prefix="rv-", dir="/tmp"))
    except OSError:
        return {"schema_version": "1", "mode": "verification",
                "readiness_state": "unavailable",
                "checks": [observation(phase, "unavailable", "temporary_storage_unavailable")
                           for phase in (*PHASES, "cleanup")]}
    os.chmod(workspace, 0o700)
    previous = signal.getsignal(signal.SIGTERM)
    previous_alarm = signal.getsignal(signal.SIGALRM)
    def interrupted(signum, frame):
        raise VerificationInterrupted()
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGALRM, interrupted)
    signal.alarm(deadline_seconds)
    cleanup_failed = False
    try:
        automation(checks, workspace)
        restore_archive(checks, workspace)
    except VerificationInterrupted:
        checks.append({"id": "execution", "phase": "classification",
                       "state": "unavailable", "reason": "verification_timeout"})
    except VerificationFailure as error:
        checks.append({"id": "execution", "phase": "classification",
                       "state": error.state, "reason": error.reason})
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError):
        checks.append({"id": "execution", "phase": "classification",
                       "state": "failed", "reason": "invalid_recovery_input"})
    finally:
        signal.alarm(0)
        # A second signal must not interrupt cleanup. Outer adapter retains a
        # bounded grace period and independently reports forced termination.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        try:
            shutil.rmtree(workspace)
        except (OSError, VerificationFailure):
            cleanup_failed = True
        signal.signal(signal.SIGTERM, previous)
        signal.signal(signal.SIGALRM, previous_alarm)
    for phase in PHASES:
        if not any(check["phase"] == phase for check in checks):
            checks.append(observation(phase, "skipped", "execution_interrupted"))
    checks.append(observation("cleanup", "failed" if cleanup_failed else "passed",
                              "cleanup_failed" if cleanup_failed else "temporary_resources_removed"))
    if cleanup_failed:
        checks[-1]["resource_reference"] = "temporary://" + workspace.name
    states = {check["state"] for check in checks}
    state = next((value for value in ("failed", "unavailable", "skipped")
                  if value in states), "passed")
    return {"schema_version": "1", "mode": "verification",
            "readiness_state": state, "checks": checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deadline-seconds", type=int, choices=range(1, 241), default=240)
    args = parser.parse_args()
    result = verify(args.deadline_seconds)
    sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
    return {"passed": 0, "failed": 1, "unavailable": 4, "skipped": 3}[result["readiness_state"]]


if __name__ == "__main__":
    raise SystemExit(main())
