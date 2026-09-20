# Media stack

This directory is the canonical Git-managed definition for Plex, Sonarr, Radarr,
SABnzbd, and Prowlarr.

Two Compose projects are deliberately retained:

- `plex.yml` uses the existing `media` project identity.
- `acquisition.yml` uses the existing `media-acquisition` project identity and its
  existing external `media-acquisition_media-network` network.

That boundary preserves container names, Docker network identity, and the legacy
book-service project, which remains out of scope. The deployed payload is copied by
Ansible to `/srv/homelab/compose/media/`; it does not use a server-side Git checkout.

All service state remains at its audited legacy bind paths under `/srv/docker`,
`/srv/downloads`, and `/mnt/wood-server-nas/media`. `/srv/docker/media` and
`/srv/docker/media-acquisition` remain rollback sources only and are not deleted by
this migration.

Plex receives its existing `PLEX_CLAIM` value from the external
`/srv/homelab/secrets/homelab.env` systemd environment file. No secret is committed.
Validate both payloads locally with:

```bash
docker compose -f compose/media/plex.yml config
docker compose -f compose/media/acquisition.yml config
```

qBittorrent and every book service are intentionally absent.
