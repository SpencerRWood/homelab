# homelab

The source of truth for Beelink-specific host configuration and home-only services.
The Beelink is both the managed deployment target and the always-on execution host for
the isolated homelab GitHub Actions runner. The MacBook can bootstrap or develop changes,
but is not required for routine CI/CD.
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
feature branch -> PR validation -> main -> semantic-release tag -> Beelink runner -> Ansible -> Beelink
```

Ansible configures hosts; Docker Compose runs applications; Terraform belongs to
provisionable/cloud infrastructure. Production configuration is not edited manually
over SSH and a Beelink checkout is not the source of truth.

## Ansible and inventory

The managed host alias is `swood-server`. Its non-secret inventory connection uses the
MacBook SSH alias, which resolves to the Beelink LAN address; authentication remains
outside Git. The top-level playbook contains only implemented roles, in this order:
storage, compose, and systemd. Storage manages the adopted NFS contracts; compose
deploys and validates canonical Compose payloads and their server-side secret file; and
systemd manages the mount-gated media startup unit.

The storage role declaratively owns the audited `media`, `database`, and
`backup_server` NFS fstab contracts. It validates the already-active mounts before
adopting them and does not request a mount, unmount, or remount during the ownership
transfer. See [storage.md](docs/storage.md).

Media workloads use a separate, mount-gated systemd startup unit. It controls Plex,
Sonarr, Radarr, SABnzbd, and Prowlarr without coupling Docker globally to NAS storage;
see [media-startup.md](docs/media-startup.md).

## Compose and migration

`compose/postgres/` owns the dedicated, internal-only Postgres runtime for home-only
application databases. `compose/media/` contains the canonical definitions for Plex, Sonarr, Radarr, SABnzbd,
and Prowlarr; `compose/books/` owns Calibre, Calibre-Web, Audiobookshelf, bookshelf
services, and ebook-importer; `compose/productivity/` owns Mealie, Vikunja, OpenProject,
and Overleaf; and `compose/platform/` owns Caddy and Vaultwarden, with staged
definitions for code-server, Grafana, Loki, and Alloy. Those containers are
intentionally stopped pending later recreation. Ansible deploys the payloads under
`/srv/homelab/compose/`; legacy `/srv/docker`
files remain rollback artifacts and are not deleted. Initial migrations preserve
images/tags, paths, volumes, UID/GID, ports, networks, configuration sources, and
database dependencies. They reuse current server state paths; state normalization to
`/srv/homelab/state/` is a later, separately validated action.
See [persistent-state.md](docs/persistent-state.md) and
[service-migration-policy.md](docs/service-migration-policy.md). The attended
[Postgres migration inventory](docs/postgres-migration.md) records ownership,
backup/rollback, and validation boundaries; infrastructure-development databases stay
on the shared wood-data-platform Postgres.

## Secrets

Runtime secrets originate in the control-node `homelab.env`, which is ignored by Git
and loaded with direnv. Ansible copies that exact file without logging values to
`/srv/homelab/secrets/homelab.env` (root:root, `0600`); canonical Compose projects
read that server-side file. Use [homelab.env.example](homelab.env.example) as a
names-only contract; never commit the runtime file, vault material, private keys, or
API tokens. Legacy `/srv/docker` secret files remain rollback material until their
corresponding cutovers are validated.

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
The PR wrapper calls `validate.yml@v1` with the same `.github/release.toml`
capabilities that gate semantic release.
Releases are semantic versions of the deployable repository configuration state, not
application-image versions: `v0.1.0` is the foundation, `v0.2.x` owns NFS storage,
and `v0.3.0` owns mount-gated media startup, including its passed reboot validation.
Conventional commits determine release bumps.

Each published GitHub Release starts the deployment workflow. It checks out the
exact `vX.Y.Z` release on the dedicated Beelink self-hosted runner, runs validation
and the canonical homelab playbook against the Beelink, then runs
`scripts/health-check.sh`. Deployments are serialized by `deploy-homelab`; a newer
release never cancels an active configuration run. A failed apply or health check
applies the previously successful `homelab` Environment release once and rechecks
it. This restores configuration only; it never attempts a blind database rollback.
Automatic and manual deployment entrypoints use the same
`.github/workflows/deploy-target.yml` configuration.

Use **Actions → Deploy released homelab configuration → Run workflow** to deploy a
specific existing release, or leave the release input empty to redeploy the latest.
The self-hosted runner retains a protected runner-local copy of the deployment input
outside the Actions checkout; runtime secrets remain protected server-side.

Renovate uses the same PR → validation → main → semantic-release → release-tag
deployment path as human changes. Docker patch, minor, major, and security image
updates are currently configured for GitHub auto-merge, including minor and major
updates. This is the existing policy; changing it requires a separate decision.
Until `main` requires the `validation` check, GitHub cannot enforce that
Renovate waits for validation. A pgvector tag
that changes PostgreSQL compatibility (for example `pg16` to `pg17`) remains manual.

## Validation

Run from the repository root:

```bash
ansible-inventory --graph
ansible-playbook ansible/playbooks/homelab-host.yml --syntax-check
ansible-playbook ansible/playbooks/homelab-host.yml --tags storage --check --diff
ansible-playbook ansible/playbooks/homelab-host.yml --tags media_startup --check --diff
docker compose -f compose/media/plex.yml config
docker compose --env-file homelab.env -f compose/postgres/compose.yml config
docker compose -f compose/media/acquisition.yml config
docker compose -f compose/books/compose.yml config
docker compose -f compose/productivity/recipes/compose.yml config
docker compose -f compose/productivity/vikunja/compose.yml config
docker compose -f compose/productivity/openproject/compose.yml config
docker compose -f compose/productivity/overleaf/compose.yml config
docker compose -f compose/platform/caddy/compose.yml config
docker compose -f compose/platform/logging/compose.yml config
docker compose -f compose/platform/code-server/compose.yml config
docker compose -f compose/platform/vaultwarden/compose.yml config
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
