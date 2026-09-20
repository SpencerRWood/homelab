# Remaining Compose ownership migration inventory

Audited on 2026-09-20 from the running `swood-server` Docker state and its legacy
Compose definitions. Environment variable names and external source paths were audited;
secret values were not collected or copied.

| Service group | Legacy project / file | Target stack | Persistent state | Database / bootstrap | Network and ingress | Restart | Cutover note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Mealie | `recipes` / `/srv/docker/recipes/docker-compose.yml` | Productivity | `/srv/docker/recipes/config/data` | External `wood-data-postgres` | `proxy`, external `wood-data-platform-db` | `unless-stopped` | Preserve `.env.resolved` as its temporary external secret source. |
| Vikunja + init | `tasks` / `/srv/docker/tasks/docker-compose.yml` | Productivity | `tasks_vikunja_db`, `tasks_vikunja_files` | `vikunja-init` must run before the app; external Postgres | `proxy`, external `wood-data-platform-db` | init `no`; app `unless-stopped` | Retain project name `tasks` so named volumes remain identical. |
| OpenProject suite | `projects` / `/srv/docker/projects/docker-compose.yml` | Productivity | `projects_projects_opdata`; legacy theme override binds | cache, seeder, web, worker, cron, Hocuspocus; external Postgres | existing `projects_default`, `proxy`, external `wood-data-platform-db` | seeder `on-failure`; other services `unless-stopped` | Retain project name `projects`; do not move its database or theme patch. |
| Overleaf suite | `docs` / `/srv/docker/docs/docker-compose.yml` | Productivity | bind dirs `overleaf_data`, `mongo_data`, `redis_data`; anonymous Mongo `/data/configdb` volume | Mongo and Redis local to the stack | existing `docs_default`, `proxy` | app/Redis `always`; Mongo `unless-stopped` | Declare the discovered anonymous Mongo config volume external by exact ID; retain project name `docs`. |
| Grafana, Loki, Alloy | `logging` / `/srv/docker/logging/docker-compose.yml` | Platform | `/srv/docker/logging/data/*` and audited config binds | Grafana uses external Postgres; Alloy depends on Loki | existing `logging`, `proxy`, external `wood-data-platform-db` | `unless-stopped` | Copy only non-secret configuration payloads into canonical Git; retain `.env.resolved` temporarily. |
| code-server + init | `code` / `/srv/docker/code/docker-compose.yml` | Platform | `code_code_server_home`, `/srv/docker/code/workspace`, `/home/spencerwood/projects` | `code-server-init` must run before the app; local image build | `proxy` | init `no`; app `unless-stopped` | Retain project name `code`; canonical payload includes the audited Dockerfile. |
| Vaultwarden | `private` / `/srv/docker/private/docker-compose.yml` | Platform | `/srv/docker/private/config/vaultwarden` | External Postgres; `private` also contains excluded infrastructure services | existing `private_default`, `proxy`, external `wood-data-platform-db` | `unless-stopped` | Isolate as its own canonical project and declare `private_default` external, so Keycloak and Infisical remain outside this repository. |
| Caddy | `proxy` / `/srv/docker/proxy/docker-compose.yml` | Platform | `proxy_caddy_data`, `proxy_caddy_config`; Caddyfile/site binds | Local Cloudflare-enabled image build | existing external `proxy`; host `192.168.1.21:80/443` | `unless-stopped` | Preserve exact build, ports, network, configuration, and external `.env.resolved`; validate Caddy before recreation. |

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
- `/srv/homelab/secrets/homelab.env` is not currently present. Canonical project
  directories will therefore receive an Ansible-managed `.env` symlink to each
  audited legacy `.env` or `.env.resolved` source; secret values remain outside Git
  and no secret-source consolidation is attempted in this migration.
- No image, database, secret, port, UID/GID, network, or ingress change is in scope.
- Before each attended cutover, compare the canonical rendered configuration with the
  audited Compose/runtime contract, run scoped Ansible check mode, and verify health,
  mounts, networks, restart policy, and proxy reachability afterward.
