"""Readiness must fail closed while permitting intentionally staged services."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HealthTests(unittest.TestCase):
    def run_health(self, state="running healthy", missing=False, docker_down=False,
                   inspection_fails=False):
        with tempfile.TemporaryDirectory() as directory:
            docker = Path(directory) / "docker"
            docker.write_text("""#!/usr/bin/env bash
set -eu
if [[ "$1" == container ]]; then
  [[ "$DOCKER_DOWN" == false ]]
  if [[ "$CADDY_MISSING" == false ]]; then echo caddy; fi
elif [[ "$2" == --format ]]; then
  [[ "$INSPECTION_FAILS" == false ]]
  printf '%s\n' "$CONTAINER_STATE"
else
  exit 1
fi
""")
            docker.chmod(0o755)
            return subprocess.run(
                ["bash", str(ROOT / "scripts/health-check-remote.sh")],
                env={**os.environ, "PATH": directory + os.pathsep + os.environ["PATH"],
                     "CONTAINER_STATE": state, "CADDY_MISSING": str(missing).lower(),
                     "INSPECTION_FAILS": str(inspection_fails).lower(),
                     "DOCKER_DOWN": str(docker_down).lower()},
                text=True, capture_output=True, timeout=10,
            )

    def test_deployed_baseline_passes_optional_services_can_be_absent(self):
        result = self.run_health()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("OK caddy", result.stdout)
        self.assertIn("SKIP mealie", result.stdout)

    def test_required_baseline_cannot_be_absent(self):
        self.assertNotEqual(0, self.run_health(missing=True).returncode)

    def test_docker_unavailable_cannot_be_reported_as_staged(self):
        self.assertNotEqual(0, self.run_health(docker_down=True).returncode)

    def test_inspection_failure_cannot_be_reported_as_absent(self):
        self.assertNotEqual(0, self.run_health(inspection_fails=True).returncode)

    def test_non_running_and_unready_states_fail(self):
        for state in ("running starting", "running unhealthy", "exited none", "", "malformed"):
            with self.subTest(state=state):
                self.assertNotEqual(0, self.run_health(state=state).returncode)

    def test_running_container_without_healthcheck_is_supported(self):
        self.assertEqual(0, self.run_health(state="running none").returncode)


if __name__ == "__main__":
    unittest.main()
