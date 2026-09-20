# homelab

The source of truth for Beelink-specific host configuration and home-only services.
The MacBook is the Ansible control node; the Beelink is a managed deployment target.
Retained services are still running from the legacy Beelink deployment and are **not**
managed by this repository yet.

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
.github/       Validation-only CI
```

## Workflow

```text
MacBook -> edit/test/commit -> GitHub -> Ansible/deployment automation -> Beelink
```

Ansible configures hosts; Docker Compose runs applications; Terraform belongs to
provisionable/cloud infrastructure. Production configuration is not edited manually
over SSH and a Beelink checkout is not the source of truth.

## Ansible and inventory

The managed host alias is `swood-server`. Its inventory connection uses the existing
local SSH-config alias `swood`, avoiding repository-stored credentials or duplicated
connection information. The top-level playbook establishes this stable role order:
base, users, storage, docker, directories, permissions, networking, security, systemd,
github_runner, and backup. Roles are intentionally interfaces only at this stage.

The storage role is the next implementation priority. It models the `media`, `database`,
and `backup_server` NFS mount contracts but deliberately does not discover, mount,
unmount, or alter the currently active mounts.

## Compose and migration

Compose directories document intended ownership; they contain no service definitions yet.
Initial migrations preserve images/tags, paths, volumes, UID/GID, ports, networks,
configuration sources, and database dependencies. They reuse current server state paths;
state normalization to `/srv/homelab/state/` is a later, separately validated action.
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

## Validation

Run from the repository root:

```bash
ansible-inventory --graph
ansible-playbook ansible/playbooks/beelink.yml --syntax-check
ansible-playbook ansible/playbooks/beelink.yml --check
pre-commit run --all-files
```

`--check` is the only permitted evaluation mode for the provisioning playbook until a
reviewed implementation is ready; do not apply it during this repository-initialization
phase.
