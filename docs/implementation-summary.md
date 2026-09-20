# Initial implementation summary

## Completed scope

This repository establishes the MacBook-authored source of truth for the Beelink
homelab. It defines the safe ownership boundary, Ansible inventory and role order,
non-secret storage and host contracts, runtime-secret policy, migration policies, and
validation-only continuous integration.

## Next steps

1. Restore GitHub authentication, create the private `SpencerRWood/homelab` repository,
   add it as `origin`, and push `main`.
2. Review the audited values for users, UID/GID mappings, LAN addressing, NAS addressing,
   and NFS exports before assigning values in `ansible/host_vars/swood-server.yml`.
3. Implement and review the storage role's preflight checks before any declarative mount
   management; do not alter the currently active mounts during that work.
4. Migrate retained services one at a time, preserving their existing runtime contracts
   and testing a rollback before each cutover.

## Explicit non-actions

No Beelink services, mounts, Docker workloads, infrastructure resources, DNS, or real
credentials were modified. Decommissioned services (Dashy, Wiki, ntfy, and qBittorrent)
and portable infrastructure workloads remain outside this repository.
