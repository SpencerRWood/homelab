# Canonical media Compose migration

## Scope and ownership

The Git repository is the canonical definition. Ansible deploys `compose/media/plex.yml`
and `compose/media/acquisition.yml` to `/srv/homelab/compose/media/`. The existing
`/srv/docker/media/docker-compose.yml` and
`/srv/docker/media-acquisition/docker-compose.yml` remain intact as temporary rollback
artifacts, but `homelab-media.service` uses only the canonical paths after cutover.

Plex retains project identity `media`. Sonarr, Radarr, SABnzbd, and Prowlarr retain
project identity `media-acquisition`; this retains their existing external
`media-acquisition_media-network` while leaving book services untouched. The external
`proxy` network remains external.

## Cutover plan

1. Confirm the media NFS mount, existing service health, Docker restart policy `no`,
   and legacy Compose validation.
2. Back up the two legacy Compose files and their non-secret metadata under the existing
   migration-backup root.
3. Transfer the existing Plex claim value from the legacy protected environment file to
   `/srv/homelab/secrets/homelab.env` without exposing it in Git.
4. Apply only the `media_startup` Ansible tag to create the canonical deployment
   directory, copy the two Compose files, and update/reload the unit.
5. Restart `homelab-media.service`. Compose project labels/config-file paths change, so
   recreating the five containers is expected; bind-mounted state, images, ports, and
   networks must remain unchanged.
6. Verify container health, Plex reachability, mounted paths, restart policies, image
   IDs, ports, networks, and no unexpected named volumes.
7. Reboot and repeat the media-startup verification.

Expected interruption is the short container recreation window during the systemd
restart. No NAS data or application state is moved.

## Validation result

The canonical cutover completed with the original images, bind mounts, ports, and
networks intact. All five containers now carry canonical Compose file labels; no named
volumes were created. The media mount remained NFSv3, Plex returned a successful HTTP
redirect on port 32400, and Sonarr, Radarr, SABnzbd, and Prowlarr became healthy.

The required attended reboot validation also passed. The boot journal shows the
mount-gated unit starting Plex first and then the four acquisition services from the
canonical paths.

## Rollback

Keep the legacy Compose files and restore the v0.3.0 systemd Compose paths:

```text
/srv/docker/media/docker-compose.yml
/srv/docker/media-acquisition/docker-compose.yml
```

Reload systemd and restart `homelab-media.service`. This returns the unit to the
already reboot-validated legacy-path architecture. Keep the five containers at restart
policy `no`; only use `unless-stopped` as an emergency fallback.
