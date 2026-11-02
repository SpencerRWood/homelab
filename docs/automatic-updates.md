# Automatic main delivery

Renovate enables GitHub platform PR automerge for eligible Docker digest pins,
digest refreshes, patch and minor updates. Other update types default to manual
merge. GitHub merges with a merge commit only after protected-main requirements
pass: `validation / validation`, `pr-routing`, resolved review threads and a
branch current with main. Renovate refreshes behind-main branches through its
native `behind-base-branch` mechanism. Conflicts must be resolved before merging.
The repository enables platform automerge and currently requires zero approving
reviews. If a human-review requirement is introduced, automerge must wait for it;
Renovate does not approve or bypass reviews.

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

OpenProject, Mealie and Vikunja version upgrades and floating-tag
digest changes retain compatibility review. A digest-only update to an exact
`X.Y.Z`, `vX.Y.Z` or `X.Y.Z-slim` application version is eligible for automerge.
Hocuspocus also permits patch updates from an exact `X.Y.Z` tag within its current
minor release: it has no database or persistent volume. Its minor and major
upgrades retain coordinated OpenProject review. Vaultwarden uses an exact stable
version plus digest and also permits patch upgrades within its current minor
release after CI. Its minor, major, prerelease and floating-tag changes retain
compatibility review. PostgreSQL/pgvector changes,
including digest refreshes, always retain persistent-state and engine
compatibility review. All major upgrades retain review. Once reviewed and
merged, these changes follow the same automatic delivery path.

A digest change on `17-slim` or `latest` can hide an application upgrade and
schema migrations; it is not an exact-version rebuild. Review the target OCI
version and upstream migrations before authorizing these protected updates.
Exact-version digest eligibility does not authorize a database-engine change,
destructive migration, permission change or unsafe schema downgrade. Required
CI, security checks, backup verification, deployment authorization, recovery and
health gates remain in force. The pinned release and deployment workflows are
unchanged by this Renovate policy.
The Vaultwarden default names the existing digest's OCI version, `1.37.4`, without
changing the selected image. PR #142's `latest` digest moves from `1.37.4` to
`1.37.5`; Renovate must recalculate it against the exact tag before it qualifies as
a patch update. Do not manually merge the stale floating-tag proposal.
Temporary GitHub mergeability results can be retried on subsequent Renovate runs;
`platformAutomerge` and `behind-base-branch` remain enabled so rebases restore
platform automerge and rerun required checks. Persistent conflicts or failed
checks still block merging.
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
OpenProject runs its tracked seeder once before recreating new web, worker, or
cron processes. A failed migration stops the rollout, and a version-changing
migration prevents unattended schema rollback.

The existing deployment recovery step restores only attempted services using the
retained exact old image IDs and previous definitions. It never pulls a floating
rollback image. A changed or unknown application version blocks unattended
downgrade because schema compatibility is unverified; recovery then stops for
manual investigation. Deployment metadata records apply, health and recovery
outcomes; root-owned `routine-update.json` retains per-container image evidence.

BusyBox permission-helper updates copy and verify the canonical Compose definition
even when the application image is unchanged. The reconciler supports only the
tracked `code-server-init` and `vikunja-init` ownership commands and pinned BusyBox
images. It snapshots the actual previous canonical definitions before copying,
then verifies the applied file contents against the prepared transaction.
For active consumers it checks the fresh recovery backup, retains the old image,
runs the helper alone with no dependencies, and verifies its exact image,
successful exit and unchanged consumer health. A disabled consumer receives the
configuration update with helper execution explicitly deferred in the transaction;
neither the consumer nor its helper is started. Updating an application image and
its permission helper together requires separate deployments.

Once an ownership helper starts, unattended rollback is blocked: an older image
cannot undo partial volume permission changes. A failed helper requires manual
investigation using the saved configuration, retained image and backup evidence.
The transaction records the target digest, selected image ID, attempted execution,
completion or deferral, and the configuration hashes used by health verification.

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
