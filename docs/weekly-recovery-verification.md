# Weekly local recovery verification (OP-497)

This consumer advertises `verification` through `scripts/weekly_recovery.py`.
It has no provider Python dependency. The version-controlled policy in
`recovery/weekly-policy.json` approves only `recovery/weekly.yml` for local
idempotence, with a zero second-run change allowance, and pins the representative
backup by SHA-256. The classification entries identify host tasks this tier cannot
prove: credential resolution, live storage/mounts, service startup.
Unsupported/skipped tasks within the approved check-mode playbook fail verification.

Run locally with `uv run scripts/weekly_recovery.py`; no host inventory, release,
remote URI or service credentials are accepted. The provider's explicitly trusted
adapter additionally requires a clean checkout, matching owner and exact revision.
The direct consumer command is useful for local diagnosis before commit.

The checked-in tar archive contains synthetic health/library route data. The
verifier checks the archive's checksum, exact regular-file member set, containment,
32-member/one-MiB extraction limits and restored file hashes. Links, devices,
duplicate entries and traversal fail. It extracts only to new mode-0700
`/tmp/rv-*` storage, serves the restored data on a temporary loopback HTTP port,
and checks both health and library responses. The listener is closed afterward.
The approved Ansible playbook copies canonical books Compose and renders the real
media readiness template into temporary storage. That shell file is syntax checked;
it is never executed and cannot start services or wait on live mounts.

Raw command output and restored contents are never emitted. JSON evidence contains
fixed reasons, phase results and artifact hashes. Cleanup is a separate result;
failed cleanup makes verification fail. Operation deadlines are 30 seconds (45
for Ansible), the declared consumer deadline is 300 seconds, and no operation is
retried. An internal 240-second run deadline and SIGTERM stop phase execution
immediately and enter bounded cleanup;
the provider allows 15 seconds before force termination. Hard-kill/worker loss
cannot attest to cleanup and must remain UNKNOWN until independently reconciled.

Exit codes are 0 passed, 1 failed, 3 skipped and 4 unavailable. A local representative
success proves executable recovery mechanisms, not freshness/restorability of all
retained live backups, production application health or blank-host reconstruction.
Existing daily dependencies/backups remain authoritative for their readiness checks.
Full host drills, reporting and production orchestration belong to later Stories.

Tests run through `uv run python -m unittest discover -s tests` and the repository's
full Wood validation. Integration tests report missing tools as skipped; mocked
failures are not a substitute for the recorded real local run. No images or
deployments are part of this Story's local validation.

`wood repo verify --json` runs the required `weekly-local-recovery` check. That
entrypoint uses a 40-second internal deadline, leaving cleanup time within Wood's
60-second bound. Wood retains the normalized record and full sanitized output.
