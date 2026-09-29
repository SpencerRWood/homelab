# Persistent-state policy

## Current state

Completed Compose cutovers retained their existing state locations, such as
`/srv/docker/media/config/plex` and
`/srv/docker/media-acquisition/config/services/sonarr`. The staged code-server and
observability definitions also refer to retained state; those applications remain
stopped. Existing `/srv/docker` trees therefore still contain live application state,
configuration, and recovery inputs. Do not remove them as obsolete deployments.

## Future normalization

State may be migrated deliberately to
`/srv/homelab/state/`, potentially with directories for Plex, Sonarr, Radarr, SABnzbd,
Prowlarr, Calibre, Calibre-Web, Audiobookshelf, Caddy, Grafana, Loki, Alloy, code-server,
Mealie, Vikunja, OpenProject, Overleaf, and Vaultwarden.

No state normalization is implemented by the current Ansible roles.

## Dedicated homelab Postgres

The dedicated Postgres runtime is a separate persistent workload. Its canonical
state location is
`/srv/homelab/state/postgres/data`, owned by the image's Postgres UID/GID (`999:999`)
with mode `0700`. It must never share, copy, or mount the shared
wood-data-platform PGDATA directory. Application databases were moved through
attended logical backup and restore. The obsolete shared source databases were
subsequently removed; their protected logical dumps, recorded in
[Postgres migration](postgres-migration.md), are the database recovery source.
