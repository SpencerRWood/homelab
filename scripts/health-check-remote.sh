#!/usr/bin/env bash
set -euo pipefail

# Absent containers are intentionally staged/not yet migrated, not unhealthy.
for container in caddy plex sonarr radarr sabnzbd prowlarr calibre ebook-importer mealie vikunja projects-web vaultwarden; do
  if ! docker inspect "$container" >/dev/null 2>&1; then
    echo "SKIP $container (not deployed)"
    continue
  fi
  inspection=$(docker inspect "$container")
  grep -q '"Running": true' <<<"$inspection"
  ! grep -q '"Status": "unhealthy"' <<<"$inspection"
  echo "OK $container"
done
