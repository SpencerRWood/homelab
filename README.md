# homelab

The source of truth for Beelink-specific host configuration and home-only services.
The Beelink is both the managed deployment target and the always-on execution host for
the isolated homelab GitHub Actions runner. The MacBook can bootstrap or develop changes,
but is not required for routine CI/CD.
The retained media, books, productivity, Caddy, and Vaultwarden services completed
their canonical Compose cutovers. Observability and code-server are intentionally
stopped with repository definitions staged for later recreation.

## Boundary

This repository defines the Beelink host and home-service boundary. Implemented
automation manages NAS mounts, Compose payloads, media startup, dedicated Postgres,
runtime secret resolution, and the homelab runner. Other host prerequisites are not
yet asserted by its roles. The separate `infrastructure` repository owns portable
platform hosts,
centralized Postgres, Dagster, shared Keycloak, Infisical, Open WebUI, RudderStack,
website-portfolio staging, other portable nonprod/prod workloads, and Terraform-managed
cloud infrastructure. Ambiguous services must be documented before placement.

## Layout

```text
ansible/       Inventory, host contracts, playbooks, and ordered host roles
compose/       Home-only stacks: media, books, platform, productivity, Postgres
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
outside Git. The top-level playbook prepares protected Infisical runtime files, then
runs storage, compose, systemd, and GitHub runner roles. Storage manages the adopted
NFS contracts; compose deploys and validates payloads and starts dedicated Postgres;
systemd manages the mount-gated media startup unit. Other Compose payloads are not
automatically recreated by every release.

The storage role declaratively owns the audited `media`, `database`, and
`backup_server` NFS fstab contracts. It validates the already-active mounts before
adopting them and does not request a mount, unmount, or remount during the ownership
transfer. See [storage.md](docs/storage.md).

Media workloads use a separate, mount-gated systemd startup unit. It controls Plex,
Sonarr, Radarr, SABnzbd, and Prowlarr without coupling Docker globally to NAS storage;
see [media-startup.md](docs/media-startup.md).

## Compose and migration

The repository owns an internal-only Postgres runtime for home application databases.
Ansible deploys canonical Compose files under `/srv/homelab/compose/`. Existing
`/srv/docker` state paths remain in use, and legacy Compose files are retained for
recovery. See [persistent state](docs/persistent-state.md), the
[migration policy](docs/service-migration-policy.md), and the
[Postgres recovery record](docs/postgres-migration.md).

## Secrets

Mealie, Vikunja, OpenProject, Caddy, and Vaultwarden secrets come from the
`Homelab` Infisical project through the root-owned resolver on the Beelink.
The `homelab-deployer` identity has
organization `no-access` and project-wide `Viewer`; application containers receive
generated env files, never Infisical credentials. See
[the runtime secret architecture](docs/infisical-runtime.md).

Other runtime and Compose interpolation inputs still originate in the control-node
`homelab.env`, which is ignored by Git and loaded with direnv. Ansible copies that
file without logging values to `/srv/homelab/secrets/homelab.env` (root:root,
`0600`). Use
[homelab.env.example](homelab.env.example) as a names-only contract; never commit
runtime files, vault material, private keys, or API tokens.

## Status and exclusions

| State | Services |
| --- | --- |
| Canonical Compose cutover completed | Plex, Sonarr, Radarr, SABnzbd, Prowlarr; Calibre, Calibre-Web, Audiobookshelf, bookshelf-audiobooks, bookshelf-ebooks, ebook-importer; Mealie, Vikunja, OpenProject, Overleaf; Caddy, Vaultwarden |
| Defined here, intentionally stopped pending recreation | code-server, Grafana, Loki, Alloy |
| Running from legacy Compose | None on `swood-server` at the 2026-09-29 inspection; all running home-service containers had canonical `/srv/homelab/compose/` labels |
| Decommissioned | Dashy, Wiki, ntfy, qBittorrent |

The media unit starts the five media services; Ansible starts dedicated Postgres.
Books and most other cut-over applications retain Docker restart behavior; selected
Infisical-backed services have service-specific boot reconciliation. The deployment
health check tests only containers already present; the 2026-09-29 host inspection
separately confirmed the states above. See the
[ownership and recovery inventory](docs/compose-ownership-migration-inventory.md)
and [migration backups](docs/migration-backups.md) for detail.

Portable infrastructure workloads, including Dagster, Keycloak, Infisical, Open WebUI,
infrastructure Postgres, CloudBeaver, and wood-data-platform are intentionally absent.

## Release model

```text
MacBook branch → pre-commit → PR → centralized validation → main
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
Run `uv run pre-commit install` in each local checkout. The installed hook
blocks development commits directly to `main`. The GitHub `main` ruleset
requires the PR validation check. Semantic-release tags the validated merged
commit without writing a new commit to `main`; see the
[shared branch policy](https://github.com/SpencerRWood/workflows/blob/main/docs/branch-rules.md).

Releases are semantic versions of the deployable repository configuration state,
not application-image versions.
Conventional commits determine release bumps.
The release job calculates the next version, tags the validated merged `main`
commit `vX.Y.Z`, and publishes the GitHub Release. The Git tag is the version
source for this non-package repository.

Each published GitHub Release starts the deployment workflow. It checks out the
exact `vX.Y.Z` release on the dedicated Beelink self-hosted runner, runs validation
and the canonical homelab playbook against the Beelink, then runs
`scripts/health-check.sh`. Deployments are serialized by `deploy-homelab`; a newer
release never cancels an active configuration run. A failed apply or health check
applies the previously successful `homelab` Environment release once and rechecks
it. This restores configuration only; it never attempts a blind database rollback.
Automatic and manual deployment enter the same `.github/workflows/deploy.yml`.
It contains the target's runner, inventory, protected input path, health command,
and durable state path. The shared resolver verifies a requested published
release or selects the latest for a manual run with no release input.

Use **Actions → Deploy released homelab configuration → Run workflow** to deploy a
specific existing release, or leave the release input empty to redeploy the latest.
The self-hosted runner retains a protected runner-local copy of the deployment input
outside the Actions checkout; runtime secrets remain protected server-side.

The [shared rollback contract](docs/rollback-contract.md) exposes `rollback.yml`
and a versioned JSON result for deterministic previous-known-good recovery.
It requires matching failed-deployment evidence, uses the canonical privileged
entrypoint, and verifies recovery separately from execution. Preview is the default.

Renovate uses the same PR → validation → main → semantic-release → release-tag
deployment path as human changes. Docker patch, minor, major, and security image
updates are currently configured for Renovate-managed PR auto-merge, including minor and major
updates. This is the existing policy; changing it requires a separate decision.
GitHub does not currently require the consumer `validation` check before a PR
can merge. Renovate-managed PR automerge waits for passing checks. A pgvector tag
that changes PostgreSQL compatibility (for example `pg16` to `pg17`) remains manual.

## Validation

Run the repository checks from the repository root:

```bash
uv run pre-commit run --all-files
```

Do not run an unrestricted live apply from documentation. Recreation of the stopped
services remains attended maintenance work with documented recovery inputs.

## Template compatibility

This is primarily an Ansible, Docker Compose, YAML, shell/helper tooling, and
documentation repository—not a Python package. It adopts the shared release and
repository-tooling conventions without force-fitting a Python application template.
Potential future template: `template-infrastructure` or `template-ansible`.
