# Initial implementation summary

## Current state

The private `SpencerRWood/homelab` repository is the MacBook-authored source of truth
for the Beelink homelab. The centralized release workflow is active and the v0.1.0
foundation release succeeded. The repository defines the safe ownership boundary,
Ansible inventory and role order, runtime-secret policy, migration policies, and
validation.

The v0.2.x releases take declarative ownership of the three existing NFS mount records
while preserving their active runtime mounts. v0.3.0 adds
[`homelab-media.service`](media-startup.md), which owns mount-gated boot startup for
the selected media workloads. Its attended reboot validation passed.

## Next steps

1. Transition remaining retained services one at a time, preserving their existing
   runtime contracts and testing a rollback before each cutover.

## Explicit non-actions

The canonical media and books Compose cutovers passed. The productivity cutover also
passed its attended reboot validation: Mealie, Vikunja, OpenProject, and a fresh
Overleaf stack returned with Caddy ingress intact. Canonical platform payloads for
Grafana, Loki, Alloy, code-server, and Vaultwarden are prepared for an attended cutover;
Caddy remains separate because it owns ingress and certificate state. Persistent state
normalization remains out of scope; existing state paths and legacy Compose files remain
rollback artifacts. Decommissioned services (Dashy, Wiki, ntfy, and qBittorrent) and
portable infrastructure workloads remain outside this repository.
