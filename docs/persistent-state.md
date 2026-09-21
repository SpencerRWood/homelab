# Persistent-state policy

## Initial Compose migration

The first migration changes only Compose ownership. New definitions reuse their current
state locations, such as `/srv/docker/media/config/plex` and
`/srv/docker/media-acquisition/config/services/sonarr`, rather than relocating state.
This keeps the transition to homelab Compose ownership reversible and narrow.

## Future normalization

After each new deployment is proven, state may be migrated deliberately to
`/srv/homelab/state/`, potentially with directories for Plex, Sonarr, Radarr, SABnzbd,
Prowlarr, Calibre, Calibre-Web, Audiobookshelf, Caddy, Grafana, Loki, Alloy, code-server,
Mealie, Vikunja, OpenProject, Overleaf, and Vaultwarden.

This task creates neither server-side paths nor migrations.

## Dedicated homelab Postgres

The new, dedicated Postgres runtime is a new persistent workload rather than a
relocation of an existing one. Its canonical state location is
`/srv/homelab/state/postgres/data`, owned by the image's Postgres UID/GID (`999:999`)
with mode `0700`. It must never share, copy, or mount the shared
wood-data-platform PGDATA directory. Application data moves only through attended
logical backup and restore; the original shared data remains the rollback source.
