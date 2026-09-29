# Compose ownership and recovery inventory

The contracts below were audited on 2026-09-20 from the then-running `swood-server`
Docker state and legacy Compose definitions. Cutover results were recorded during
subsequent attended migrations. The current repository deploys all listed canonical
payloads, but deployment only copies and validates most files. A read-only
2026-09-29 host inspection confirmed that the cut-over services were running with
`/srv/homelab/compose/` config-file labels. The four staged applications were exited
with `/srv/docker/` labels; no running home service had a legacy Compose label.
Environment variable names and external source paths were audited; secret values
were not copied.

| Service group | Legacy project / file | Canonical stack | Persistent state | Database / bootstrap | Network and ingress | Restart | Recorded status / recovery note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Mealie | `recipes` / `/srv/docker/recipes/docker-compose.yml` | Productivity | `/srv/docker/recipes/config/data` | Dedicated `homelab-postgres` | `proxy`, internal `homelab-postgres` | `unless-stopped` | Canonical cutover passed; source database cleanup completed. |
| Vikunja + init | `tasks` / `/srv/docker/tasks/docker-compose.yml` | Productivity | `tasks_vikunja_db`, `tasks_vikunja_files` | `vikunja-init` runs before the app; dedicated Postgres | `proxy`, internal `homelab-postgres` | init `no`; app `unless-stopped` | Canonical cutover passed; project name `tasks` retains volume identity. |
| OpenProject suite | `projects` / `/srv/docker/projects/docker-compose.yml` | Productivity | `projects_projects_opdata`; legacy theme override binds | cache, seeder, web, worker, cron, Hocuspocus; dedicated Postgres | existing `projects_default`, `proxy`, external `database_default`, internal `homelab-postgres` | seeder `on-failure`; other services `unless-stopped` | Canonical cutover passed; theme patch and legacy network remain. |
| Overleaf suite | `docs` / `/srv/docker/docs/docker-compose.yml` | Productivity | bind dirs `overleaf_data`, `mongo_data`, `redis_data`; anonymous Mongo `/data/configdb` volume | Mongo and Redis local to the stack | existing `docs_default`, `proxy` | app/Redis `always`; Mongo `unless-stopped` | Fresh stack passed cutover and reboot validation; the discovered Mongo config volume is declared external by exact ID. |
| Grafana, Loki, Alloy | `logging` / `/srv/docker/logging/docker-compose.yml` | Staged Platform (`compose/platform/logging`) | `/srv/docker/logging/data/*` and audited config binds | Grafana database restored to dedicated Postgres; Alloy depends on Loki | existing `logging`, `proxy`, internal `homelab-postgres` | `unless-stopped` | Intentionally stopped pending later recreation; no canonical application cutover recorded. |
| code-server + init | `code` / `/srv/docker/code/docker-compose.yml` | Staged Platform (`compose/platform/code-server`) | `code_code_server_home`, `/srv/docker/code/workspace`, `/home/spencerwood/projects` | `code-server-init` must run before the app; local image build | `proxy` | init `no`; app `unless-stopped` | Intentionally stopped on 2026-09-21 pending later recreation. Retain the legacy project, canonical payload, image, named volume, workspace, and configuration; restart with `docker compose start` from `/srv/docker/code`. |
| Vaultwarden | `private` / `/srv/docker/private/docker-compose.yml` | Platform (`compose/platform/vaultwarden`) | `/srv/docker/private/config/vaultwarden` | Dedicated Postgres; `private` also contains excluded infrastructure services | existing `private_default`, `proxy`, internal `homelab-postgres` | `unless-stopped` | Canonical cutover passed; source database cleanup completed. |
| Caddy | `proxy` / `/srv/docker/proxy/docker-compose.yml` | Platform (`compose/platform/caddy`) | `proxy_caddy_data`, `proxy_caddy_config`; Caddyfile/site binds | Local Cloudflare-enabled image build | existing external `proxy`; host `192.168.1.21:80/443` | `unless-stopped` | Canonical cutover passed on 2026-09-21. It preserves the `proxy` project name, volumes, build module, ports, network, and legacy config binds; the legacy project and pre-cutover image tag remain rollback artifacts. |

## Excluded projects

`dagster`, `chat` (Open WebUI), `wood-data-platform`, its Postgres and CloudBeaver
subprojects, and the `private` project's Infisical and Keycloak services are portable or
infrastructure workloads and remain outside this repository. Dashy, Wiki, ntfy, and
qBittorrent are absent and must remain absent.

## Cutover constraints

- All canonical files retain legacy project identity where it owns named volumes or a
  non-external default network.
- Existing `/srv/docker` trees remain state, configuration, secret-source, and rollback
  artifacts. No state is moved or deleted.
- The Ansible deployment uses `/srv/homelab/secrets/homelab.env` for Compose
  interpolation and links platform project `.env` files to it. Selected application
  secrets now use protected Infisical-resolved runtime files; see
  [Infisical runtime](infisical-runtime.md). Secret values remain outside Git.
- Before recreating a stopped service, compare rendered configuration with its
  audited runtime contract and verify health, mounts, networks, restart policy,
  database connection, and proxy reachability afterward.
- Caddy and Vaultwarden now use Infisical-backed runtime files. For secret-source
  rollback, use the service-specific commands in [Infisical runtime](infisical-runtime.md).
  The pre-cutover Caddy image tag, legacy proxy tree, and Caddy volumes remain
  recovery inputs for the original Compose ownership cutover.
- Observability rollback/restart: run `docker compose start` from `/srv/docker/logging`.
  Do not remove the logging Compose files, images, configuration, or persistent data.
- code-server rollback/restart: run `docker compose start` from `/srv/docker/code`.
  Do not remove the code-server Compose file, image, named volume, workspace, or configuration.
- The pre-cutover Vaultwarden image tag, legacy private project, and `/data` bind
  remain recovery inputs for the original Compose ownership cutover.
