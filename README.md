# homelab

The source of truth for Beelink-specific host configuration and home-only services.
The MacBook is the Ansible control node; the Beelink is a managed deployment target.
Retained services are still running from the legacy Beelink deployment and are **not**
managed by this repository yet, except Plex, Sonarr, Radarr, SABnzbd, and Prowlarr,
which are managed from the canonical media Compose payload.

## Boundary

This repository owns the Beelink baseline, users/groups/permissions, NAS and storage
prerequisites, Docker, home ingress, backup prerequisites, and home-only Compose
definitions. The separate `infrastructure` repository owns portable platform hosts,
centralized Postgres, Dagster, shared Keycloak, Infisical, Open WebUI, RudderStack,
website-portfolio staging, other portable nonprod/prod workloads, and Terraform-managed
cloud infrastructure. Ambiguous services must be documented before placement.

## Layout

```text
ansible/       Inventory, host contracts, playbooks, and ordered host roles
compose/       Future home-only stacks: media, books, platform, productivity
docs/          Architecture and migration policies
scripts/       Optional local helper scripts
.github/       Centralized-release consumer configuration
```

## Workflow

```text
MacBook -> edit/test/commit -> GitHub -> Ansible/deployment automation -> Beelink
```

Ansible configures hosts; Docker Compose runs applications; Terraform belongs to
provisionable/cloud infrastructure. Production configuration is not edited manually
over SSH and a Beelink checkout is not the source of truth.

## Ansible and inventory

The managed host alias is `swood-server`. Its non-secret inventory connection uses the
MacBook SSH alias, which resolves to the Beelink LAN address; authentication remains
outside Git. The top-level playbook establishes this stable role order:
base, users, storage, docker, directories, permissions, networking, security, systemd,
github_runner, and backup. The playbook defines the intended host-baseline role order.
Roles are implemented incrementally: storage and media startup ownership are currently
managed declaratively, while other roles may still be interface placeholders.

The storage role declaratively owns the audited `media`, `database`, and
`backup_server` NFS fstab contracts. It validates the already-active mounts before
adopting them and does not request a mount, unmount, or remount during the ownership
transfer. See [storage.md](docs/storage.md).

Media workloads use a separate, mount-gated systemd startup unit. It controls Plex,
Sonarr, Radarr, SABnzbd, and Prowlarr without coupling Docker globally to NAS storage;
see [media-startup.md](docs/media-startup.md).

## Compose and migration

`compose/media/` contains the canonical definitions for Plex, Sonarr, Radarr, SABnzbd,
and Prowlarr; `compose/books/` owns Calibre, Calibre-Web, Audiobookshelf, bookshelf
services, and ebook-importer. Ansible deploys them under `/srv/homelab/compose/`; legacy
`/srv/docker` files remain rollback artifacts and are not deleted. Initial migrations
preserve images/tags, paths, volumes, UID/GID, ports, networks, configuration sources,
and database dependencies. They reuse current server state paths; state normalization to
`/srv/homelab/state/` is a later, separately validated action.
See [persistent-state.md](docs/persistent-state.md) and
[service-migration-policy.md](docs/service-migration-policy.md).

## Secrets

Runtime secrets live outside Git, by default at `/srv/homelab/secrets/homelab.env`.
Use [homelab.env.example](homelab.env.example) as a names-only contract; never commit
the runtime file, vault material, private keys, or API tokens.

## Status and exclusions

Phase 1 audit and migration preparation are complete; retained configuration/state has
recovery inputs documented in [migration-backups.md](docs/migration-backups.md). No
retained service was changed by repository initialization.

Dashy, Wiki, ntfy, and qBittorrent were decommissioned and are intentionally absent.
Portable infrastructure workloads, including Dagster, Keycloak, Infisical, Open WebUI,
infrastructure Postgres, CloudBeaver, and wood-data-platform are intentionally absent.

## Release model

```text
MacBook
  ↓
pre-commit
  ↓
GitHub main
  ↓
SpencerRWood/workflows@v1
  ↓
validation
  ↓
semantic-release
  ↓
homelab vX.Y.Z
```

The thin [release workflow](.github/workflows/release.yml) runs only for pushes to
`main` and delegates validation and release creation to the stable centralized
workflow contract. Pull requests do not run privileged or self-hosted workloads.
Releases are semantic versions of the deployable repository configuration state, not
application-image versions: `v0.1.0` is the foundation, `v0.2.x` owns NFS storage,
and `v0.3.0` owns mount-gated media startup, including its passed reboot validation.
Conventional commits determine release bumps.

Release is not deployment. A release may create tags, GitHub releases, changelog
metadata, and versioned source/configuration artifacts, but it never SSHes to the
Beelink, runs Ansible against it, runs Docker Compose, restarts containers, or changes
mounts. Deployment automation remains a separate future concern, introduced only after
the Ansible host baseline is validated, the persistent-state strategy is proven,
retained-service migration is stable, and rollback mechanisms exist.

## Validation

Run from the repository root:

```bash
ansible-inventory --graph
ansible-playbook ansible/playbooks/homelab-host.yml --syntax-check
ansible-playbook ansible/playbooks/homelab-host.yml --tags storage --check --diff
ansible-playbook ansible/playbooks/homelab-host.yml --tags media_startup --check --diff
docker compose -f compose/media/plex.yml config
docker compose -f compose/media/acquisition.yml config
docker compose -f compose/books/compose.yml config
pre-commit run --all-files
```

Do not run an unrestricted live apply from documentation. The media Compose cutover and
post-cutover reboot validation have passed; subsequent service migrations remain
attended maintenance actions with documented rollbacks.

## Template compatibility

This is primarily an Ansible, Docker Compose, YAML, shell/helper tooling, and
documentation repository—not a Python package. It adopts the shared release and
repository-tooling conventions without force-fitting a Python application template.
Potential future template: `template-infrastructure` or `template-ansible`.
