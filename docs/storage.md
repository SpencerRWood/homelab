# NFS storage policy

## Topology

`swood-server` consumes three NFSv3 exports from the NAS at `192.168.1.10`:

| Export | Mountpoint | Runtime requirement |
| --- | --- | --- |
| `/volume1/media` | `/mnt/wood-server-nas/media` | Yes; workload handling follows later |
| `/volume1/database` | `/mnt/wood-server-nas/database` | No |
| `/volume1/backup_server` | `/mnt/wood-server-nas/backup_server` | No |

The Ansible storage role manages the host-side NFS client package and one fstab record
per mount. It validates the existing mounted source before adopting a record and
continues to assert the live mount after convergence.

## Persistent mount options

Every record uses `nfsvers=3,rw,hard,_netdev,nofail`.

NFSv3 and `hard` preserve the audited behavior. `_netdev` identifies a network-backed
filesystem. `nofail` remains a host boot policy: the host can start without the NAS.
It is deliberately separate from workload policy; media workloads will eventually have
their own startup gate instead of making Docker globally depend on the NAS.

`intr` is intentionally absent. It is legacy, no longer part of the effective runtime
contract, and must not be carried into the declarative fstab state.

## Safety, validation, and rollback

The role uses `ansible.posix.mount` with `state: present`, which changes only fstab.
It does not invoke a mount, unmount, remount, or broad `mount -a`. Before a non-check
mutation, it copies `/etc/fstab` to a unique root-owned backup named
`/etc/fstab.pre-homelab-<UTC timestamp>` and preserves its owner, group, and mode.

If a source changes unexpectedly, a mount disappears, an ordinary directory appears at
a mountpoint, duplicate records are created, unrelated fstab content changes, or a
workload loses storage access, restore the saved fstab backup and stop further
automation. Do not improvise follow-on changes during rollback.

The separately deployed `homelab-media.service` now owns media workload startup
ordering after the NAS mount is ready. The former Plex boot workaround was removed
during that transition; see [media startup](media-startup.md).
