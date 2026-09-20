# Media startup ownership

`homelab-media.service` owns boot-time startup for Plex, Sonarr, Radarr, SABnzbd,
and Prowlarr. It is enabled at `multi-user.target`, requires Docker, requests the
media mount through `RequiresMountsFor=`, and waits for the audited Movies and TV Shows
directories before invoking the existing legacy Compose projects.

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

If rollback is required before a reboot, restore `unless-stopped` for the five media
containers, disable the unit, and restore the saved user-crontab backup made during
cron removal. Do not reboot-test this transition until separately scheduled.
