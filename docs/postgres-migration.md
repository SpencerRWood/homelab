# Dedicated homelab Postgres migration

## Ownership and release boundary

Homelab owns the `homelab-postgres` Docker Compose runtime for home-only services.
The first release deploys an empty PostgreSQL 16 instance only. It does not create
application schemas, change connection strings, or alter the shared instance.
The shared `wood-data-platform` instance remains the interim owner of
infrastructure-development databases and must not be decommissioned by this work.

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
credential values.

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
| `mealie` | active Mealie connection; canonical homelab Compose | homelab | `mealie` | logical backup/restore; cut over alone |
| `openproject` | active OpenProject web/worker connections; canonical homelab Compose | homelab | `openproject` | logical backup/restore; cut over alone |
| `vaultwarden` | active Vaultwarden connection; canonical homelab Compose | homelab | `vaultwarden` | logical backup/restore; cut over alone |
| `vikunja` | canonical homelab Compose; no active connection during audit | homelab | `vikunja` | logical backup/restore before its cutover |
| `grafana` | homelab-owned staged configuration, container currently stopped | homelab | `grafana` | retain source; migrate only with its later attended recreation |
| `dagster`, `infisical`, `keycloak`, `openwebui` | active portable-infrastructure services excluded by homelab boundary | infrastructure-dev | matching role | leave on shared instance |
| `portfolio_website` | website-portfolio explicitly excluded | infrastructure-dev | `portfolio_migrator`, `portfolio_runtime` | leave on shared instance |
| `synthetic_website_data` | portable development-data workload | infrastructure-dev | `wood`, `synthetic_website_editor`, `dbt_editor` | leave on shared instance |
| `wood_data` | data-platform default database | system/internal | `wood` | leave on shared instance |
| `postgres` | administrative default database | system/internal | `wood` | leave on shared instance |

`cloudbeaver_readonly` is a system/internal utility role and must not be migrated.
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
receives that service's connections. Source database deletion is explicitly deferred
to a later cleanup release after observation and backup/restore validation.
