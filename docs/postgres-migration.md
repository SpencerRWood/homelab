# Dedicated homelab Postgres migration

## Ownership and release boundary

Homelab owns the `homelab-postgres` Docker Compose runtime for home-only services.
The first release deploys an empty PostgreSQL 16 instance only. It does not create
application schemas, change connection strings, or alter the shared instance.
The shared `wood-data-platform` instance now owns only infrastructure-development
and system/internal databases and must not be decommissioned by this work.

The target image is `pgvector/pgvector:0.8.2-pg16-bookworm`, intentionally matching
the live shared instance's PostgreSQL 16 major version (live runtime reported
PostgreSQL 16.14). The target has no host `ports` mapping: applications will use the
internal Docker network `homelab-postgres` and hostname `homelab-postgres` after their
individual cutovers. Persistent data is `/srv/homelab/state/postgres/data` and the
container uses `PGDATA=/var/lib/postgresql/data/pgdata`.

Secrets flow only through the ignored control-node `homelab.env`, loaded by direnv,
then Ansible to `/srv/homelab/secrets/homelab.env` (`root:root`, `0600`). The target
requires `HOMELAB_POSTGRES_SUPERUSER` and
`HOMELAB_POSTGRES_SUPERUSER_PASSWORD`; this document intentionally contains no
credential values. The Postgres-tagged Ansible run refuses to start the service if
either value is absent or blank.

## Shared-instance audit — 2026-09-21

Live state was treated as authoritative and compared with
`wood-data-platform/compose.postgres.yaml`.

| Contract | Source configuration | Live runtime |
| --- | --- | --- |
| Image/version | `pgvector/pgvector:0.8.2-pg16-bookworm` | PostgreSQL 16.14 |
| Container/project | `wood-data-postgres` / `wood-data-platform` | same |
| Host access | source says `expose: 5432` only | `192.168.1.21:25432->5432/tcp` |
| Networks | `wood-data-platform-db` internal | also attached to `wood-data-platform-lan` |
| PGDATA/storage | configured external bind | `/srv/data-platform/postgres/data` -> `/var/lib/postgresql/data` |
| Storage permissions | not asserted in source | `dnsmasq:root`, `0700` on data directory |
| Restart/healthcheck | `unless-stopped`; `pg_isready` every 10s, 5 retries | same |
| Initialization | read-only entrypoint bind | `/srv/docker/wood-data-platform/platform/postgres/init` (present; no live init files) |
| Backups | configured root: `/mnt/wood-server-nas/database/backups` | no current artifact inventory was returned during audit; Phase 5 creates and verifies per-database logical backups before any restore |

The shared runtime uses bind mounts, not a named volume: its PGDATA bind, its
entrypoint-init bind, and its Docker-secret password bind are all separate from the
new runtime. Never use `docker compose down -v`, raw PGDATA copying, or a dual mount.

## Database classification and target action

| Database | Owner/service evidence | Classification | Current role | Target action |
| --- | --- | --- | --- | --- |
| `mealie` | active Mealie connection; canonical homelab Compose | homelab | `mealie` | migrated; source database/role removed 2026-09-21 |
| `openproject` | active OpenProject web/worker connections; canonical homelab Compose | homelab | `openproject` | migrated; source database/role removed 2026-09-21 |
| `vaultwarden` | active Vaultwarden connection; canonical homelab Compose | homelab | `vaultwarden` | migrated; source database/role removed 2026-09-21 |
| `vikunja` | canonical homelab Compose; no active connection during audit | homelab | `vikunja` | migrated; source database/role removed 2026-09-21 |
| `grafana` | homelab-owned staged configuration, container currently stopped | homelab | `grafana` | logically restored; application cutover deferred until later recreation |
| `dagster`, `infisical`, `keycloak`, `openwebui` | active portable-infrastructure services excluded by homelab boundary | infrastructure-dev | matching role | leave on shared instance |
| `portfolio_website` | website-portfolio explicitly excluded | infrastructure-dev | `portfolio_migrator`, `portfolio_runtime` | leave on shared instance |
| `synthetic_website_data` | portable development-data workload | infrastructure-dev | `wood`, `synthetic_website_editor`, `dbt_editor` | leave on shared instance |
| `wood_data` | data-platform default database | system/internal | `wood` | leave on shared instance |
| `postgres` | administrative default database | system/internal | `wood` | leave on shared instance |

`cloudbeaver_readonly` is a system/internal utility role and was not migrated.
No obsolete/unknown database had evidence sufficient for migration.

## Roles, grants, extensions, and connection contract

All application roles are login roles without superuser, createdb, or createrole
privileges. `wood` is the shared superuser. The only observed role memberships are
the standard `pg_monitor` memberships. Each listed application database is owned by
its application role; its `public` schema is owned by `pg_database_owner`.
CloudBeaver has `CONNECT` grants on selected shared databases; those grants are not
part of the homelab migration unless independently required.

| Database | Extensions beyond `plpgsql` | Current hostname / credential source |
| --- | --- | --- |
| `mealie` | `pg_trgm 1.6` | `wood-data-postgres`; `MEALIE_POSTGRES_PASSWORD` in canonical secret file |
| `openproject` | `btree_gist 1.7`, `pg_trgm 1.6`, `unaccent 1.1` | shared database network; `DATABASE_URL` in canonical secret file |
| `vaultwarden` | none | shared database network; `VAULTWARDEN_DATABASE_URL` in canonical secret file |
| `vikunja` | none | `wood-data-postgres`; `VIKUNJA_DATABASE_PASSWORD` in canonical secret file |
| `grafana` | none | `wood-data-postgres:5432`; `GRAFANA_POSTGRES_PASSWORD` in canonical secret file |

Before each database restore, capture `pg_dumpall --globals-only`, a custom-format
`pg_dump`, database ACLs, schema owners, extension versions, table counts, and size
outside Git under the existing migration-backup root. Create the target dedicated role
with its existing password (no incidental rotation), restore logically, and retain
the source database unchanged. The rollback for each application is its unchanged
legacy Compose/environment connection plus the still-running shared source database.

## Validation record and next release

First-release acceptance requires `docker compose config --quiet`, target health,
reported PG16 version, target mount inspection, no published target port, container
restart survival, and an idempotent Ansible `--check --diff`. Host reboot validation
is attended and recorded only if performed. The migration release records per-service
HTTP/read/write/permission evidence and verifies that the shared instance no longer
receives that service's connections.

### First-release validation — 2026-09-21

The empty target was deployed through `ansible-playbook ... --tags postgres` after
its bootstrap secrets were supplied. It reported `healthy`, PostgreSQL 16.14,
`unless-stopped`, an empty host-port binding set, and an internal-only
`homelab-postgres` network. Its bind mount is
`/srv/homelab/state/postgres/data` to `/var/lib/postgresql/data`; the host directory
is `999:999`, mode `0700`. A dedicated container restart returned to healthy status
and retained the expected empty database list (`postgres`). The subsequent Ansible
`--tags postgres --check --diff` run reported zero changes. No host reboot was
performed outside an attended maintenance window.

### Logical backup preparation — 2026-09-21

Before any restore, protected custom-format dumps, checksums, role metadata, and
per-database size/table-count/extension inventories were created at
`/mnt/wood-server-nas/backup_server/homelab-migration/20260921T090024EDT-postgres-phase5`.
Artifacts exist for `mealie`, `openproject`, `vaultwarden`, `vikunja`, and `grafana`.
They are mode `0600` in a mode-`0700` directory and are deliberately outside Git.
The shared source instance remains unchanged and is the rollback source.

### Mealie target restore — 2026-09-21

`mealie` was restored to the dedicated runtime from its protected custom-format
backup. Its target role retains the source password hash and remains a non-superuser
login role. Source and target both report `14 MB`, 66 public tables, and
`pg_trgm 1.6` plus `plpgsql 1.0`; target database ownership is `mealie` and the role
has `CONNECT`. The source-only `cloudbeaver_readonly` database grant was intentionally
excluded from the target restore because CloudBeaver is system/internal and outside
the homelab boundary. The source `mealie` database remains unchanged for rollback.

### Mealie cutover validation — 2026-09-21

The canonical Mealie payload now uses hostname `homelab-postgres` and only the
internal `homelab-postgres` plus existing `proxy` networks. Mealie was recreated by
itself, reached `healthy`, returned HTTP 200 from `/api/app/about`, and logged a
successful PostgreSQL initialization. The dedicated database reported two Mealie
connections; the shared source reported none. No database-permission or migration
error was logged. An authenticated create/update check is deferred to an attended
user session; rollback remains the retained `/srv/docker/recipes/docker-compose.yml`
configuration and unchanged shared source database.

### Grouped remaining-service restore and cutover — 2026-09-21

During the approved maintenance window, `vikunja`, `openproject`, and `vaultwarden`
were restored from their protected custom-format backups to the dedicated runtime.
All retain their original non-superuser application roles and source credentials.
The source-only CloudBeaver ACL was excluded. Source and target table counts and
extensions match: Vikunja 37/`plpgsql`; OpenProject 210/`btree_gist`, `pg_trgm`,
`plpgsql`, `unaccent`; Vaultwarden 29/`plpgsql`.

The canonical Vikunja, OpenProject, and Vaultwarden payloads now attach to
`homelab-postgres`; OpenProject retains its separate `legacy-database` network
unchanged. The three workloads were recreated during one attended window. OpenProject
and Vaultwarden reached healthy status, Vikunja remained running and logged successful
migrations, and no database permission or migration error was observed. Active
OpenProject connections are present on the dedicated database and none of the three
applications had an active connection on the shared source during the post-cutover
inspection. Authenticated create/update checks remain attended user-session work.

### Grafana staged database migration — 2026-09-21

The stopped Grafana workload was not recreated. Its database and dedicated role were
logically restored to the target, where source and target both report 13 MB, 87 public
tables, and `plpgsql 1.0`. Its staged Compose definition now defaults to
`homelab-postgres:5432` and attaches to the dedicated network, so a later attended
Grafana recreation does not restore the shared-Postgres dependency.

### Legacy shared-source cleanup — 2026-09-21

After explicit application-data confirmation, all five custom-format backups and
inventories were checksum-verified. The shared instance had no active connections for
the homelab applications. Only then were its obsolete `mealie`, `vikunja`,
`openproject`, `vaultwarden`, and `grafana` databases and matching roles removed.
The remaining non-template databases are `dagster`, `infisical`, `keycloak`,
`openwebui`, `portfolio_website`, `postgres`, `synthetic_website_data`, and
`wood_data`; none were altered. The obsolete ignored local `POSTGRES_*` connection
variables were removed. Rollback after this cleanup requires restoring the protected
logical dumps, rather than reconnecting to a retained source database.
