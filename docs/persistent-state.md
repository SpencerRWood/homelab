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
