#!/usr/bin/env python3
"""Resolve Mealie's one runtime secret from Infisical without logging values."""

import json
import os
import pathlib
import re
import stat
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request


IDENTITY = pathlib.Path("/srv/homelab/secrets/bootstrap/infisical-mealie.json")
DESTINATION = pathlib.Path("/srv/homelab/secrets/runtime/mealie.env")
KEY = "POSTGRES_PASSWORD"


def protected_file(path: pathlib.Path) -> None:
    details = path.stat()
    if not stat.S_ISREG(details.st_mode) or details.st_uid != 0 or stat.S_IMODE(details.st_mode) != 0o600:
        raise ValueError("protected file ownership or permissions are invalid")


def resolve() -> None:
    if os.geteuid() != 0:
        raise ValueError("run as root")
    os.umask(0o077)
    protected_file(IDENTITY)
    identity = json.loads(IDENTITY.read_text(encoding="utf-8"))
    if set(identity) != {"client_id", "client_secret", "project_id", "api_url"}:
        raise ValueError("identity configuration has unexpected fields")
    api_url = identity["api_url"].rstrip("/")
    if not api_url.startswith("https://"):
        raise ValueError("Infisical endpoint must use HTTPS")
    form = urllib.parse.urlencode(
        {"clientId": identity["client_id"], "clientSecret": identity["client_secret"]}
    ).encode("utf-8")
    request = urllib.request.Request(
        api_url + "/api/v1/auth/universal-auth/login",
        data=form,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Infisical-Mealie-Resolver/1.0",
        },
        method="POST",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=15) as response:
        token = json.load(response)["accessToken"]
    if not isinstance(token, str) or not token:
        raise ValueError("machine identity returned no access token")

    DESTINATION.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory = DESTINATION.parent.stat()
    if directory.st_uid != 0 or stat.S_IMODE(directory.st_mode) != 0o700:
        raise ValueError("runtime directory ownership or permissions are invalid")
    export_fd, export_path = tempfile.mkstemp(prefix="mealie-export-", dir=DESTINATION.parent)
    os.close(export_fd)
    try:
        env = os.environ.copy()
        env["INFISICAL_TOKEN"] = token
        env["INFISICAL_API_URL"] = api_url
        env["INFISICAL_DOMAIN"] = api_url
        env["INFISICAL_DISABLE_UPDATE_CHECK"] = "true"
        command = [
            "infisical", "export", "--format=json", "--env=homelab",
            "--path=/mealie", "--projectId=" + identity["project_id"],
            "--domain=" + api_url, "--expand=false", "--include-imports=false",
            "--telemetry=false", "--silent",
            "--output-file=" + export_path,
        ]
        result = subprocess.run(command, env=env, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=45, check=False)
        if result.returncode:
            raise ValueError("Infisical export failed")
        protected_file(pathlib.Path(export_path))
        exported = json.loads(pathlib.Path(export_path).read_text(encoding="utf-8"))
        if not isinstance(exported, list) or len(exported) != 1:
            raise ValueError("Mealie destination must contain only POSTGRES_PASSWORD")
        secret = exported[0]
        if not isinstance(secret, dict) or any(
            secret.get(field) != expected
            for field, expected in (
                ("key", KEY),
                ("workspace", identity["project_id"]),
                ("secretPath", "/mealie"),
                ("type", "shared"),
            )
        ):
            raise ValueError("Mealie destination metadata is invalid")
        value = secret.get("value")
        if not isinstance(value, str) or not value or "\n" in value or "\r" in value or "\x00" in value:
            raise ValueError("Mealie secret is not a nonempty single-line value")
        if not re.fullmatch(r"[\x21-\x7e]+", value):
            raise ValueError("Mealie secret contains unsupported characters")

        runtime_fd, runtime_path = tempfile.mkstemp(prefix="mealie-runtime-", dir=DESTINATION.parent)
        try:
            with os.fdopen(runtime_fd, "w", encoding="utf-8") as stream:
                stream.write(KEY + "=" + value + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(runtime_path, 0o600)
            os.replace(runtime_path, DESTINATION)
        finally:
            if os.path.exists(runtime_path):
                os.unlink(runtime_path)
    finally:
        if os.path.exists(export_path):
            os.unlink(export_path)
    print("POSTGRES_PASSWORD homelab /mealie resolved")


if __name__ == "__main__":
    try:
        resolve()
    except Exception:
        print("Mealie secret resolution failed; existing runtime file was not replaced", file=sys.stderr)
        sys.exit(1)
