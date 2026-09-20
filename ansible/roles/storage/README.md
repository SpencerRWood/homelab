# Storage role

This role owns the audited NFS client prerequisite and the persistent `/etc/fstab`
records for `homelab_mounts`. It deliberately uses `ansible.posix.mount` with
`state: present`: it edits fstab only and never requests a mount, unmount, or remount.

Before taking ownership, preflight checks the NAS NFS port, validates every definition,
rejects duplicate paths or exports, and confirms that each existing mount is already
mounted from its exact declared source. An ordinary local directory at a mount path is
a hard failure.

When a managed fstab record will change in a non-check run, the role creates a unique,
root-owned copy at `/etc/fstab.pre-homelab-<UTC timestamp>` before the mutation. The
copy preserves the original fstab owner, group, and mode. Restore that file and stop
automation if a deployment must be rolled back.

Run the ownership transition with:

```bash
ansible-playbook ansible/playbooks/beelink.yml --tags storage --check --diff
ansible-playbook ansible/playbooks/beelink.yml --tags storage
```
