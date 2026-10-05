#!/usr/bin/env bash
set -euo pipefail

# Docker itself must be available; absent optional containers are staged.
containers=$(docker container ls --all --format '{{.Names}}')
for container in caddy plex sonarr radarr sabnzbd prowlarr calibre ebook-importer mealie vikunja projects-web vaultwarden; do
  if ! grep -Fxq "$container" <<<"$containers"; then
    if [[ "$container" == caddy ]]; then
      echo 'FAIL caddy (required deployed baseline is absent)' >&2
      exit 1
    fi
    echo "SKIP $container (not deployed)"
    continue
  fi
  state=$(docker inspect --format '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container")
  case "$state" in
    'running healthy'|'running none') ;;
    *) echo "FAIL $container (not running and ready)" >&2; exit 1 ;;
  esac
  echo "OK $container"
done
