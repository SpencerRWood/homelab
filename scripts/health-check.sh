#!/usr/bin/env bash
# Check only containers which the current host actually has deployed.  Several
# Compose definitions are intentionally staged, so an absent container is not a
# deployment failure.
set -euo pipefail

uv run ansible -i ansible/inventory/homelab.yml homelab -b -m shell -a '
set -euo pipefail
for container in caddy plex sonarr radarr sabnzbd prowlarr mealie vikunja projects-web vaultwarden; do
  if ! docker inspect "$container" >/dev/null 2>&1; then
    echo "SKIP $container (not deployed)"
    continue
  fi
  state=$(docker inspect --format "{{.State.Running}} {{if .Config.Healthcheck}}{{.State.Health.Status}}{{else}}none{{end}}" "$container")
  test "${state%% *}" = true
  test "${state##* }" != unhealthy
  echo "OK $container $state"
done
'
