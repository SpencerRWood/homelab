# Architecture

```text
MacBook
  |
  | Git + Ansible
  v
GitHub
  |
  +-------------------------------+
  |                               |
  v                               v
homelab repo                  infrastructure repo
  |                               |
  v                               v
Beelink home services         portable platform hosts
```

On the Beelink, Ansible configures the host baseline, users/groups, NAS mounts, Docker,
directories, permissions, networking/security, system services, and backup prerequisites.
Docker Compose then runs the media, books, platform, and productivity services.

Terraform provisions cloud or otherwise provisionable infrastructure. Ansible configures
hosts. Docker Compose runs application services. The Beelink is a managed deployment
target, never the authoritative Git working copy.
