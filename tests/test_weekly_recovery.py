"""Executable recovery safety and failure-path tests; no live service inputs."""

import importlib.util
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("weekly_recovery", ROOT / "scripts/weekly_recovery.py")
WEEKLY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WEEKLY)


class WeeklyTests(unittest.TestCase):
    def test_checksummed_but_unreadable_archive_is_a_restore_failure(self):
        with tempfile.TemporaryDirectory(prefix="rv-", dir="/tmp") as directory:
            root = Path(directory)
            fixture = root / "recovery/fixtures/representative.tar"
            fixture.parent.mkdir(parents=True)
            fixture.write_bytes(b"not-a-tar-archive")
            policy = json.loads((ROOT / "recovery/weekly-policy.json").read_text())
            policy["backup_sha256"] = hashlib.sha256(fixture.read_bytes()).hexdigest()
            (root / "recovery/weekly-policy.json").write_text(json.dumps(policy))
            workspace = root / "workspace"
            workspace.mkdir()
            checks = []
            with patch.object(WEEKLY, "ROOT", root):
                WEEKLY.restore_archive(checks, workspace)
            self.assertEqual("failed", checks[0]["state"])
            self.assertEqual("invalid_recovery_input", checks[0]["reason"])

    def test_real_deadline_interrupts_subprocess_and_cleans(self):
        def slow(workspace_checks, workspace):
            WEEKLY.command(["python3", "-c", "import time; time.sleep(30)"], workspace)
        with patch.object(WEEKLY, "automation", side_effect=slow):
            with patch.object(WEEKLY, "restore_archive") as restore:
                result = WEEKLY.verify(deadline_seconds=1)
        restore.assert_not_called()
        self.assertEqual("unavailable", result["readiness_state"])
        self.assertEqual("passed", result["checks"][-1]["state"])

    def test_interruption_stops_phases_and_enters_cleanup(self):
        with patch.object(WEEKLY, "automation", side_effect=WEEKLY.VerificationInterrupted()):
            with patch.object(WEEKLY, "restore_archive") as restore:
                result = WEEKLY.verify()
        restore.assert_not_called()
        self.assertEqual("unavailable", result["readiness_state"])
        self.assertEqual("passed", result["checks"][-1]["state"])

    def test_unavailable_temporary_storage_has_no_false_cleanup_claim(self):
        with patch.object(WEEKLY.tempfile, "mkdtemp", side_effect=OSError("secret")):
            result = WEEKLY.verify()
        self.assertEqual("unavailable", result["readiness_state"])
        self.assertEqual("unavailable", result["checks"][-1]["state"])
        self.assertNotIn("secret", json.dumps(result))

    def test_check_mode_unsupported_tasks_fail_closed(self):
        recap = b"localhost : ok=1 changed=0 unreachable=0 failed=0 skipped=1 rescued=0 ignored=0"
        with tempfile.TemporaryDirectory(prefix="rv-", dir="/tmp") as directory:
            with patch.object(WEEKLY, "command", return_value=recap):
                with self.assertRaises(WEEKLY.VerificationFailure) as error:
                    WEEKLY.approved_automation(Path(directory), check_mode=True)
        self.assertEqual("unsupported_check_mode_task", error.exception.reason)

    def test_idempotence_drift_and_approval_are_enforced(self):
        with tempfile.TemporaryDirectory(prefix="rv-", dir="/tmp") as directory:
            with patch.object(WEEKLY, "approved_automation", side_effect=[2, 1]):
                with self.assertRaises(WEEKLY.VerificationFailure) as error:
                    WEEKLY.idempotence(Path(directory))
            self.assertEqual("idempotence_drift", error.exception.reason)
            with patch.object(WEEKLY.json, "loads", return_value={
                "idempotence_safe": False, "allowed_second_run_changes": 0,
            }):
                with self.assertRaises(WEEKLY.VerificationFailure) as error:
                    WEEKLY.approved_automation(Path(directory))
            self.assertEqual("idempotence_not_approved", error.exception.reason)

    def test_timeout_unavailable_tool_and_output_are_bounded(self):
        with tempfile.TemporaryDirectory(prefix="rv-", dir="/tmp") as directory:
            workspace = Path(directory)
            for argv, reason in (
                (["definitely-missing-weekly-tool"], "tool_unavailable"),
                (["python3", "-c", "import time; time.sleep(30)"], "command_timeout"),
                (["python3", "-c", "print('secret-do-not-echo' * 7000)"], "output_limit_exceeded"),
                (["python3", "-c", "raise SystemExit(1)"], "command_failed"),
            ):
                with self.assertRaises(WEEKLY.VerificationFailure) as error:
                    WEEKLY.command(argv, workspace, timeout=1)
                self.assertEqual(reason, error.exception.reason)
                self.assertNotIn("secret-do-not-echo", str(error.exception))

    def test_commands_do_not_inherit_secret_or_connection_settings(self):
        with tempfile.TemporaryDirectory(prefix="rv-", dir="/tmp") as directory:
            with patch.dict(os.environ, {"SENSITIVE_TOKEN": "secret", "PGHOST": "live"}):
                output = WEEKLY.command(
                    ["python3", "-c", "import os; print('SENSITIVE_TOKEN' in os.environ or 'PGHOST' in os.environ)"],
                    Path(directory),
                )
        self.assertEqual(b"False\n", output)

    def test_cleanup_failure_is_independent_of_restore_result(self):
        captured = []
        real_mkdtemp = tempfile.mkdtemp
        def allocate(*args, **kwargs):
            value = real_mkdtemp(*args, **kwargs)
            captured.append(Path(value))
            return value
        with patch.object(WEEKLY.tempfile, "mkdtemp", side_effect=allocate):
            with patch.object(WEEKLY, "automation"):
                with patch.object(WEEKLY, "restore_archive"):
                    with patch.object(WEEKLY.shutil, "rmtree", side_effect=OSError("secret")):
                        result = WEEKLY.verify()
        try:
            cleanup = next(check for check in result["checks"] if check["phase"] == "cleanup")
            self.assertEqual("failed", cleanup["state"])
            self.assertEqual("failed", result["readiness_state"])
            self.assertNotIn("secret", json.dumps(result))
        finally:
            for path in captured:
                shutil.rmtree(path)

    def test_transient_dependency_failure_preserves_unknown_and_cleans(self):
        captured = []
        real_mkdtemp = tempfile.mkdtemp
        def allocate(*args, **kwargs):
            value = real_mkdtemp(*args, **kwargs)
            captured.append(Path(value))
            return value
        with patch.object(WEEKLY.tempfile, "mkdtemp", side_effect=allocate):
            with patch.object(WEEKLY, "automation"):
                with patch.object(WEEKLY, "restore_archive",
                                  side_effect=WEEKLY.VerificationFailure("dependency_unavailable", "unavailable")):
                    result = WEEKLY.verify()
        self.assertEqual("unavailable", result["readiness_state"])
        self.assertTrue(all(not path.exists() for path in captured))
        self.assertEqual("passed", result["checks"][-1]["state"])

    @unittest.skipUnless(shutil.which("ansible-playbook") and True,
                         "local integration requires declared verification tools")
    def test_real_weekly_recovery_and_resource_cleanup(self):
        captured = []
        real_mkdtemp = tempfile.mkdtemp
        def allocate(*args, **kwargs):
            value = real_mkdtemp(*args, **kwargs)
            captured.append(Path(value))
            return value
        with patch.object(WEEKLY.tempfile, "mkdtemp", side_effect=allocate):
            result = WEEKLY.verify()
        self.assertEqual("passed", result["readiness_state"], result)
        self.assertTrue(all(not path.exists() for path in captured))
        restore = next(check for check in result["checks"] if check["phase"] == "restore")
        self.assertRegex(restore["artifact_sha256"], "^[0-9a-f]{64}$")

    def test_corrupt_unreadable_and_failed_integrity_backup(self):
        for failure in (WEEKLY.VerificationFailure("backup_checksum_mismatch"), OSError("secret")):
            with patch.object(WEEKLY, "automation"):
                with patch.object(WEEKLY, "digest_file", side_effect=failure):
                    result = WEEKLY.verify()
            self.assertEqual("failed", result["readiness_state"])
            self.assertEqual("passed", result["checks"][-1]["state"])
            self.assertNotIn("secret", json.dumps(result))
        digest = json.loads((ROOT / "recovery/weekly-policy.json").read_text())["backup_sha256"]
        with tempfile.TemporaryDirectory(prefix="rv-", dir="/tmp") as directory:
            checks = []
            with patch.object(WEEKLY, "digest_file", side_effect=[digest, "0" * 64]):
                WEEKLY.restore_archive(checks, Path(directory))
            self.assertEqual("failed", next(c for c in checks if c["phase"] == "integrity")["state"])

    def test_archive_path_traversal_and_links_are_rejected(self):
        import io
        import tarfile
        for name, kind in (("../live", tarfile.REGTYPE), ("routes.json", tarfile.SYMTYPE)):
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode="w") as archive:
                entry = tarfile.TarInfo(name)
                entry.type = kind
                entry.linkname = "/etc/passwd" if kind == tarfile.SYMTYPE else ""
                archive.addfile(entry)
            stream.seek(0)
            with tempfile.TemporaryDirectory(prefix="rv-", dir="/tmp") as directory:
                checks = []
                original_open = tarfile.open
                with patch("tarfile.open", side_effect=lambda *a, **k: original_open(fileobj=stream, mode="r:")):
                    WEEKLY.restore_archive(checks, Path(directory))
                self.assertEqual("failed", checks[0]["state"])
                self.assertEqual([], list((Path(directory) / "restored").iterdir()))


if __name__ == "__main__":
    unittest.main()
