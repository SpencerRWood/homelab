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

1. Migrate the books stack only after explicitly resolving the ebook importer's
   anonymous `/config` volume.
2. Transition retained services one at a time, preserving their existing runtime
   contracts and testing a rollback before each cutover.

## Explicit non-actions

The canonical media Compose cutover and its attended reboot validation passed. The
current implementation does not migrate book services or normalize persistent state.
The legacy Compose files remain rollback artifacts for the known-good v0.3.0
legacy-path architecture.
Decommissioned services (Dashy, Wiki, ntfy, and qBittorrent) and portable
infrastructure workloads remain outside this repository.
