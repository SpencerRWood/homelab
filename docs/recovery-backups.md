# Recovery backups

The canonical homelab Ansible host playbook installs the repository backup
producer as `/usr/local/sbin/homelab-recovery-backup`, root-owned `0700`, with
protected configuration at `/etc/homelab/recovery-backup.json`. The existing
01:30 logical-backup schedule remains authoritative. Its managed block invokes
the new producer with `sudo -n`; the sudoers rule permits only this exact command
and protected configuration. The superseded helper is removed after its caller
is migrated. No second homelab schedule is created.

## State and consistency

All non-template databases in `homelab-postgres` are dumped, with required
OpenProject, Vaultwarden, Mealie, Vikunja and Grafana coverage. Each database has
a custom PostgreSQL archive; cluster roles and privileges are captured in
`postgres-globals.sql`. The retired migration cluster is not a source.
Credentials are resolved inside the active container through its current
PostgreSQL runtime contract, never placed in argv or manifests.

OpenProject assets, Vaultwarden files, Mealie data, Vikunja uploads, Plex and
media application state, and Calibre library metadata are separate file
artifacts. Their writers are paused while the group is captured, ensuring SQLite
files and database-related attachments are consistent. Only previously running
writers are restarted, including after a failed backup. A paused-service rollout
requires explicit operational approval; `quiesce_authorized` defaults to false
and the producer fails closed until that prerequisite is met.

Original media, books and downloads on the NAS are not included in the host
application-state archive. They require a separate NAS recovery policy and an
off-NAS copy. Caddy certificates can be reissued from repository configuration;
full service restart, secret resolution and whole-library recovery remain
separate full-application acceptance work. Never label a database or file
archive restore as full-system recovery.

## Destination and retention

The destination is
`/mnt/wood-server-nas/backup_server/swood-server/homelab`, on exactly
`192.168.1.10:/volume1/backup_server` with filesystem type `nfs`. Mount absence,
wrong source and symlink redirection fail before publication. An ordinary host
directory cannot substitute for the NAS. This copy survives application-host
loss, but shares the NAS failure domain with media. Off-NAS replication and NAS
encryption at rest are unverified. All new artifacts, including PostgreSQL roles,
database archives and application state, are encrypted with the configured age
recipient before publication. Existing backups remain untouched.

Temporary groups are private and never consumed. Complete groups contain
nonempty validated artifacts with SHA-256 checksums, source completion times,
sizes, formats and restoration prerequisites. They are renamed atomically before
`current.json` is replaced. Runs lock the destination; a failed backup preserves
every prior group and the previous pointer without refreshing its timestamp.
Completed directories use `0750` and files `0640` for verifier GID 10001, with
read access only. No secret contents appear in manifests or diagnostics.

Proposed retention: 14 daily, 8 weekly, 12 monthly recovery points. Pruning is
disabled; no existing backups are deleted. Confirm capacity and obtain separate
approval before introducing deletion. Normal attempts have a one-hour deadline;
a kernel-blocked hard NFS request may still require operator intervention.

## Operation and isolated verification

After approved rollout and consistency authorization:

The focused `ansible/playbooks/backups.yml` installs only the backup role using
the same canonical inventory variables. Preview it with `--check --diff` before
the separately approved apply. It does not run a backup.

```sh
sudo /usr/local/sbin/homelab-recovery-backup --config /etc/homelab/recovery-backup.json
scripts/weekly_recovery.py --real-backups
```

The producer emits sanitized JSON and writes its independent attempt state to
`/var/lib/homelab/backups/last-attempt.json`. Inspect this state, the actual
scheduler, mount identity, permissions and completed artifacts after deployment.
Neither a successful Ansible run nor an existing file establishes readiness.

The consumer's existing preflight interface verifies the current recovery group
against `recovery/backup-policy.yml`: consumer/environment, declared timestamps,
freshness, required coverage, size, format and checksums. Missing, stale, corrupt
or incomplete backups fail readiness. Routine deployment uses the same current
group and validation contract; it no longer accepts the migration-era manifest.

The operational weekly interface uses `--real-backups`. The unflagged command
continues to test local fixtures for development only. Real verification copies
artifacts read-only into protected disposable storage, creates a private
socket-only PostgreSQL instance under an unprivileged user, restores roles,
database ownership and ACLs, checks application schemas, runs `pg_amcheck` and
representative Mealie queries, and restores representative OpenProject assets.
It starts no production application and uses no live database URI or credential.
Required engine binaries, extensions and original database locale must be
available. Temporary cleanup is independently reported.

The published immutable manifest reports `restore_verification: not_run` at
creation. Recovery Verification records subsequent actual restore results
separately, bound to the restored artifact SHA-256 and source completion time.
Checksum validation never upgrades this state to restore or application success.

For an operator restore, validate a complete group first, restore globals before
databases with compatible PostgreSQL and extensions, retain ownership and ACLs,
and pair each file archive with its recovery group. Restore only into disposable
targets during testing. Live restoration, deployment and full-system recovery
require their separate gates. Preserve prior backups and rollback paths while
investigating any mount, artifact, schema, query or cleanup failure.

## Declarative configuration and validation

Backup targets, container identities, credential source contracts, paths,
schedule references, retention, freshness, recovery prerequisites and group
names are declared in `ansible/inventory/group_vars/homelab.yml` under
`backups_configuration`. Verification expectations and representative queries
are in `recovery/backup-policy.yml`. Both have JSON Schema validation; the
coverage check rejects missing targets, duplicate identities and mismatched
producer/verifier origin, destination or freshness. Duplicate YAML keys fail.
Adding a supported target changes YAML and its verification coverage policy;
it requires no adapter code change.

Ansible renders protected runtime JSON from canonical YAML, installs its schema,
and validates it before replacing configuration. The producer also validates
before destination writes or service interruption. Runtime JSON is a deployment
artifact, never a separate configuration authority. No deprecated JSON source
configuration is consulted. Run:

```sh
uv run --frozen python scripts/validate-backups.py ansible/inventory/group_vars/homelab.yml
```

Retention counts are declarative planning policy; destructive pruning is
schema-forbidden. The current writer-quiescence default remains false. Local
schema/test success does not authorize rollout or establish operational recovery.

Missing or unreadable artifacts are unavailable evidence. Empty, corrupt, stale
or incomplete groups are failed evidence. Both prevent readiness; only successful
isolated restoration establishes restore evidence.
