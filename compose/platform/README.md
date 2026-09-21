# Platform stacks

This directory contains the canonical home-only definitions for Caddy, Grafana, Loki,
Alloy, code-server, and Vaultwarden. Render and operate each project with
`/srv/homelab/secrets/homelab.env`; values are never committed.

Caddy's canonical payload retains the live `proxy` project name, external `proxy`
network, fixed LAN ingress bindings, Caddy named volumes, and legacy Caddyfile/site
bind mounts. Its legacy `/srv/docker/proxy` tree remains the rollback source until an
attended ingress cutover succeeds.

Dashy and ntfy were decommissioned and are excluded. Shared Keycloak, Infisical,
Dagster, Open WebUI, and centralized infrastructure Postgres belong to the separate
infrastructure repository.
