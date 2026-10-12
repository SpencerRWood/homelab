# Automatic main delivery

Renovate groups digest pins, digest refreshes, patch and minor updates. Required CI
and existing branch protection still govern squash automerge. Renovate rebases
behind-main branches through its native `behind-base-branch` mechanism.

A successful main-push validation triggers deployment for both human and Renovate
merges. Merge into main is the standing delivery authorization; no additional
publication or deployment confirmation is required. Feature branches and PR
events cannot publish or deploy. The policy checks the exact event revision on
main, without restricting authors or requiring image-only commits.

Shared validation and the branch-head check run before semantic-release. When
semantic-release publishes a new version, deployment uses that release tag. When
no new version is needed, deployment uses the exact validated main commit SHA.
Concurrent releases retain only the newest pending run. Deployment is invoked
directly; it does not depend on a GITHUB_TOKEN-generated release event triggering
another workflow.

PostgreSQL, OpenProject (including Hocuspocus), Vaultwarden, Mealie and Vikunja
retain manual PR review. Once reviewed and merged, they follow the same automatic
delivery path.
Permission-changing BusyBox init helpers also require manual review. Changes to
Caddy's shared version ARG remain a coordinated reviewed build change; its two
base digest updates are eligible for Renovate automerge.

Both main-push deployment and explicitly approved release dispatches use
`release-check`, `release-apply`, and `release-health` through the scoped Ansible
reconciler. Checking the target is an automated workflow step, not an approval
prompt. Recovery uses the same retained-image transaction in both modes. Merge
authorization does not make schema downgrades safe.

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

Merge the shared workflow PR first, then the Homelab PR pinned to its exact
provider commit. Install the corresponding runner wrapper before merging the
caller, because that merge triggers delivery. The `backups` role adds the helper
to the existing nightly job without changing its schedule. A successful backup
must produce a less-than-24-hour-old checksum-verified gzip dump and manifest for
the actual `homelab-postgres` databases, including OpenProject, Vaultwarden,
Mealie and Vikunja. The helper does not run during installation.

Deployment reconciles the current baseline with the merged revision, including
Caddy's version label and the declared disabled-service policy. Host provisioning
retains its separate Ansible playbook. Verify backup restoration on an isolated
target before applying migration-sensitive changes.
