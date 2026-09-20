# Media startup ownership

`homelab-media.service` owns boot-time startup for Plex, Sonarr, Radarr, SABnzbd,
and Prowlarr. It is enabled at `multi-user.target`, requires Docker, requests the
media mount through `RequiresMountsFor=`, and waits for the audited Movies and TV Shows
directories before invoking the canonical Compose payload under
`/srv/homelab/compose/media/`.

The unit intentionally starts only those five media workloads. Book services remain
outside this feature even though some currently share a legacy Compose project.

## Restart policy

Services that have transitioned to a repository-managed systemd startup unit use Docker
restart policy `no`. Docker must not auto-start them before their unit has confirmed
required storage. This is the architecture policy for future service transitions too;
do not change unrelated live services until each has an equivalent unit.

The media unit does not make Docker globally dependent on NAS storage. Other services
continue to follow their current startup behavior.

## Transition and rollback

The adoption enables the unit without starting it, changes only the five selected
container restart policies, and removes the legacy Plex `@reboot` cron entry. It does
not start, stop, restart, or recreate a container during adoption.

The mount-gated startup model passed its initial attended reboot validation. The
canonical Compose cutover and its second attended reboot validation also passed:
Plex starts first from `plex.yml`, followed by Sonarr, Radarr, SABnzbd, and Prowlarr
from `acquisition.yml` once the media mount is ready.

For a Compose-path rollback, restore the previous systemd unit from the v0.3.0
architecture, whose `ExecStart` commands target `/srv/docker/media/docker-compose.yml`
and `/srv/docker/media-acquisition/docker-compose.yml`, then restart the unit. Keep
restart policy `no`; do not restore `unless-stopped` unless emergency recovery requires
it.
