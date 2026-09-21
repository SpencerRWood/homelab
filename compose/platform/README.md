# Platform stacks

This directory contains the canonical home-only definitions for Caddy and Vaultwarden,
plus staged definitions for code-server, Grafana, Loki, and Alloy. Render and operate
each project with
`/srv/homelab/secrets/homelab.env`; values are never committed.

Caddy's canonical payload retains the live `proxy` project name, external `proxy`
network, fixed LAN ingress bindings, Caddy named volumes, and legacy Caddyfile/site
bind mounts. Its legacy `/srv/docker/proxy` tree remains the rollback source until an
attended ingress cutover succeeds.

Vaultwarden's canonical cutover passed on 2026-09-21. Its `/data` bind, image, and
`private_default` and `proxy` remain unchanged; Vaultwarden now uses the dedicated
internal `homelab-postgres` network.
The legacy `/srv/docker/private` project and pre-cutover image tag remain rollback
artifacts; Keycloak and Infisical remain outside this repository.

The legacy observability containers were intentionally stopped on 2026-09-21 while
their recreation is planned. Their Compose files, configuration, images, and persistent
data remain intact; restart them from `/srv/docker/logging` with `docker compose start`.

The legacy code-server and init containers were also intentionally stopped on
2026-09-21 while recreation is planned. Its Compose file, `code_code_server_home`
volume, workspace, image, and configuration remain intact; restart it from
`/srv/docker/code` with `docker compose start`.

Dashy and ntfy were decommissioned and are excluded. Shared Keycloak, Infisical,
Dagster, Open WebUI, and centralized infrastructure Postgres belong to the separate
infrastructure repository.
