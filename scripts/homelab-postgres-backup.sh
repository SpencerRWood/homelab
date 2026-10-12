#!/usr/bin/env bash
# Invoked by the existing nightly database-logical-backup job, not a new schedule.
set -euo pipefail
backup_mount=/mnt/wood-server-nas/backup_server
mountpoint -q "$backup_mount"
backup_host=$(hostname)
backup_stamp=$(date -u +%Y-%m-%dT%H-%M-%S)
backup_root="$backup_mount/$backup_host"
backup_dir="$backup_root/db-dumps/$(date -u +%Y-%m-%d)"
mkdir -p "$backup_dir" "$backup_root/logs"
artifact="$backup_dir/homelab-postgres-pg-dumpall-$backup_stamp.sql.gz"
manifest="$backup_root/logs/homelab-postgres-backup.json"
# A stopped or missing active cluster is a failed backup, never a successful skip.
test "$(docker inspect --format '{{.State.Running}}' homelab-postgres)" = true
databases=$(docker exec homelab-postgres sh -c '
  export PGPASSWORD="$POSTGRES_PASSWORD"
  exec psql -U "$POSTGRES_USER" -d postgres -Atc "SELECT datname FROM pg_database WHERE NOT datistemplate;"
')
for database in openproject vaultwarden mealie vikunja; do
  printf '%s\n' "$databases" | grep -qx "$database"
done
trap 'rm -f "$artifact.tmp" "$manifest.tmp"' EXIT
docker exec homelab-postgres sh -c '
  export PGPASSWORD="$POSTGRES_PASSWORD"
  exec pg_dumpall -U "$POSTGRES_USER"
' | gzip -9 > "$artifact.tmp"
gzip -t "$artifact.tmp"
mv "$artifact.tmp" "$artifact"
chmod 0600 "$artifact"
python3 - "$artifact" "$manifest" "$databases" <<'PY'
import datetime, hashlib, json, os, sys
artifact, manifest, databases = sys.argv[1:]
with open(artifact, 'rb') as stream:
    checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
with open(manifest + '.tmp', 'w') as stream:
    json.dump({'container': 'homelab-postgres', 'databases': databases.splitlines(),
               'artifact': artifact, 'sha256': checksum,
               'completed_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}, stream)
    stream.write('\n')
os.chmod(manifest + '.tmp', 0o600)
os.replace(manifest + '.tmp', manifest)
PY
