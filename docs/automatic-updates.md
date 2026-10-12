# Routine container delivery

Renovate groups digest pins, digest refreshes, patch and minor updates. Required CI
and existing branch protection still govern squash automerge. Renovate rebases
behind-main branches through its native `behind-base-branch` mechanism.

A main push can publish only when every commit since the previous published
release is an image-only, squash-merged Renovate PR. The repository policy rejects
major/channel changes, downgrades, unpinned references, protected packages and
unrelated changes. Shared release validation and the branch-head check run before
semantic-release. Concurrent releases retain only the newest pending run. The
verified publication output invokes deployment directly; it does not depend on a
GITHUB_TOKEN-generated release event triggering another workflow.

PostgreSQL, OpenProject (including Hocuspocus), Vaultwarden, Mealie and Vikunja
retain manual PR review and separate publication/deployment approval.
Permission-changing BusyBox init helpers also require manual review. Changes to
Caddy's shared version ARG remain a coordinated manual build change; its two base
digest updates are eligible. Other policy/configuration changes remain manual.

Both automatic and explicitly approved manual image deployments use the scoped
Ansible reconciler and its exact-image health evidence. Manual approval admits
pending manual release changes; it does not make schema downgrades safe. Recovery
uses the same retained-image transaction in both modes.

Automatic deployment checks the protected current-release metadata, fresh active
cluster backup, media mounts and effective pinned image references. It copies
only affected definitions through Ansible, retains old local image IDs, and
recreates affected running services individually with `--no-deps --no-build`.
The explicit `disabled_containers` policy preserves staged code-server and logging
services without starting or verifying them as active workloads. Unexpectedly
running disabled services and other stopped affected services block deployment.
Media services remain ordered
Plex, Sonarr, Radarr, SABnzbd, Prowlarr with the existing NAS readiness paths and
restart policies. Secrets and volumes retain their existing definitions. Caddy
builds verify the Cloudflare module and actual mounted configuration before use.
Health checks verify image ID, restart policy, health state, mod reference and
configured endpoints before proceeding to the next container.

The existing deployment recovery step restores only attempted services using the
retained exact old image IDs and previous definitions. It never pulls a floating
rollback image. A changed or unknown application version blocks unattended
downgrade because schema compatibility is unverified; recovery then stops for
manual investigation. Deployment metadata records apply, health and recovery
outcomes; root-owned `routine-update.json` retains per-container image evidence.

## Initial activation

These implementation PRs do not publish or deploy. Merge the shared workflow PR
first, then the Homelab PR pinned to its exact provider commit. The first release
containing policy/wrapper changes requires normal manual publication approval.
Before unattended deployment, separately authorize installation of the updated
runner wrapper and the `backups` role. The latter adds the active cluster helper
to the existing nightly job without changing its schedule. A successful backup
must produce a less-than-24-hour-old checksum-verified gzip dump and manifest for
the actual `homelab-postgres` databases, including OpenProject, Vaultwarden,
Mealie and Vikunja. The helper does not run during installation.

Reconcile and approve a known-good baseline manually, including Caddy's version
label and the declared disabled-service policy. Approved manual deployments use
the scoped reconciler; host provisioning retains its separate Ansible playbook.
Installation alone does not enable automatic reconciliation of
an older runtime containing protected/migration-sensitive changes. Verify the
backup restoration procedure on an isolated target before enabling unattended
stateful applications. No production operation is part of these PRs.
