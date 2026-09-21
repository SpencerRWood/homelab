# Platform stacks

This directory contains the canonical home-only definitions for Grafana, Loki, Alloy,
code-server, and Vaultwarden. Render and operate each project with
`/srv/homelab/secrets/homelab.env`; values are never committed.

Caddy remains in its legacy project pending a separately attended ingress migration.
Its live configuration and certificate state must be preserved exactly when it moves.

Dashy and ntfy were decommissioned and are excluded. Shared Keycloak, Infisical,
Dagster, Open WebUI, and centralized infrastructure Postgres belong to the separate
infrastructure repository.
