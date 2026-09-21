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
| Grafana, Loki, Alloy | `logging` / `/srv/docker/logging/docker-compose.yml` | Staged Platform (`compose/platform/logging`) | `/srv/docker/logging/data/*` and audited config binds | Grafana uses external Postgres; Alloy depends on Loki | existing `logging`, `proxy`, external `wood-data-platform-db` | `unless-stopped` | Intentionally stopped on 2026-09-21 pending later recreation. Retain the legacy project, canonical payload, images, configuration, and persistent data; restart with `docker compose start` from `/srv/docker/logging`. |
| code-server + init | `code` / `/srv/docker/code/docker-compose.yml` | Staged Platform (`compose/platform/code-server`) | `code_code_server_home`, `/srv/docker/code/workspace`, `/home/spencerwood/projects` | `code-server-init` must run before the app; local image build | `proxy` | init `no`; app `unless-stopped` | Intentionally stopped on 2026-09-21 pending later recreation. Retain the legacy project, canonical payload, image, named volume, workspace, and configuration; restart with `docker compose start` from `/srv/docker/code`. |
| Vaultwarden | `private` / `/srv/docker/private/docker-compose.yml` | Platform (`compose/platform/vaultwarden`) | `/srv/docker/private/config/vaultwarden` | External Postgres; `private` also contains excluded infrastructure services | existing `private_default`, `proxy`, external `wood-data-platform-db` | `unless-stopped` | Canonical payload isolates Vaultwarden while keeping Keycloak and Infisical outside this repository. |
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
- Canonical payloads render from `/srv/homelab/secrets/homelab.env`, which is read by
  the root-privileged Ansible deployment. It links each canonical platform project's
  `.env` to that central file. Secret values remain outside Git; the deployment
  preflight requires the file before it copies a selected stack.
- No image, database, secret, port, UID/GID, network, or ingress change is in scope.
- Before each attended cutover, compare the canonical rendered configuration with the
  audited Compose/runtime contract, run scoped Ansible check mode, and verify health,
  mounts, networks, restart policy, and proxy reachability afterward.
- Caddy rollback: retag `local/caddy-cloudflare:pre-canonical-caddy-cutover` as
  `local/caddy-cloudflare:2.11.2`, then run
  `docker compose --env-file .env.resolved up -d --no-deps --force-recreate caddy`
  from `/srv/docker/proxy`. Do not remove the legacy proxy tree or Caddy volumes.
- Observability rollback/restart: run `docker compose start` from `/srv/docker/logging`.
  Do not remove the logging Compose files, images, configuration, or persistent data.
- code-server rollback/restart: run `docker compose start` from `/srv/docker/code`.
  Do not remove the code-server Compose file, image, named volume, workspace, or configuration.
