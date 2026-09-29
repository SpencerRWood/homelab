# Migration backups

The initial migration recovery input is located at:

`/mnt/wood-server-nas/backup_server/homelab-migration/20260920T155000EDT`

It contains retained configuration/state backups, manifests, checksums, metadata,
logical database backups or reference locations, and archived declarative configuration.
Later protected logical database backups and their verification are recorded in
[Postgres migration](postgres-migration.md). The initial snapshot predates the
completed Compose and database cutovers; use the service-specific rollback records
and the latest verified database backup for recovery. No backup is copied into Git.
