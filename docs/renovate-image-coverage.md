# Renovate Docker image coverage audit — 2026-10-12

The repository had incomplete dependency discovery. The missing media PRs are
explained by filenames outside Renovate's default Compose pattern, rather than
evidence that their upstream images were unchanged. Additional gaps affected
Compose variable defaults, Dockerfile bases, and Calibre-Web's OCI mod.

The proposed configuration manages every current external image's digest.
Automatic Caddy **version** upgrades remain blocked by Renovate's shared-ARG
replacement limitation; both Caddy base digests are managed. No runtime changes
were made, and no image upgrades or digest pins are included in this audit PR.

## Scope and counts

The audit inspected all 100 files tracked at base revision
`7dadf5d9f201f051e1eb78d49a002484a6f86d0c`, including hidden workflows, every
Compose YAML, both Dockerfiles, Ansible templates/defaults/variables, scripts,
JSON/TOML declarations, and the names-only environment contract. Untracked
runtime secrets and external host configuration are outside repository scope.
Ansible copies canonical Compose and Dockerfile payloads; it has no additional
independent image declaration. Internal Docker build stage names are not images.

There are **33 configuration occurrences, 26 distinct image/channel references**:
**22 covered, 2 excluded local build outputs, and 2 partially blocked Caddy base
references**. The 24 external references all resolve successfully. Eight already
have digest pins; 16 need pins. The historical PostgreSQL migration reference is
listed separately below, bringing the inventory including historical evidence to
27 references: 22 covered, 3 excluded, 2 blocked.

The complete matrix is in [renovate-image-inventory.json](renovate-image-inventory.json).
It retains every configuration source location, service, registry, literal
expression, resolved default, discovery before/after, manager, current pin,
resolved registry digest, proposed update, policy, disposition, and PR history.
Repeated image uses remain one dependency with multiple source locations.

## Root causes and evidence

1. **Plex, Sonarr, Radarr, Prowlarr, SABnzbd:** the default pattern recognizes
   `compose*.yml`, not arbitrary names under `compose/`. Consequently
   `compose/media/plex.yml` and `compose/media/acquisition.yml` were absent from
   extraction. All five current tags resolve, and the corrected configuration
   proposes pins. Their absent previous digest means an upstream digest change
   since migration cannot be established from Git alone.
2. **Mealie, Vikunja, OpenProject, Vaultwarden, Loki, Grafana, Alloy:** the standard
   manager returns `contains-variable` for `repository:${VARIABLE:-tag}`. A scoped
   custom manager now reads and rewrites the default, preserving the variable,
   registry and tag channel, and placing the digest inside the default expression.
   Both Mealie files and all four OpenProject uses are maintained together.
3. **code-server base and Caddy bases:** `enabledManagers: ["docker-compose"]`
   disabled Dockerfile discovery. The Dockerfile manager now handles code-server.
   Caddy's shared `ARG CADDY_VERSION` with `-builder` and `-alpine` suffixes also
   defeats the standard replacement path: full dry runs extract the dependencies
   but cannot write the expected version or digest. A file-specific recursive
   custom manager now pins and refreshes each existing channel's digest. The
   standard manager is disabled only for that Dockerfile to avoid overlapping
   ownership. Caddy `2.11.7-builder` and `2.11.7-alpine` are available, but tag
   upgrades are explicitly disabled pending a coordinated build-contract change.
   Digest pinning must not introduce a new version with an old variant's digest.
4. **Calibre-Web mod:** `DOCKER_MODS: linuxserver/mods:universal-calibre` is an OCI
   reference outside normal image fields. A third custom manager covers this
   exact source and channel. LinuxServer's loader explicitly accepts tag plus
   digest; no runtime mod installation was performed.
5. **Already managed images:** the eight pinned external references resolve to
   their recorded digests and have no eligible tag/digest update in this snapshot.
   This includes the floating `latest` and `softcover` references; their healthy
   lookup is supported by a digest comparison, not by an absent PR.

The live [Dependency Dashboard #21](https://github.com/SpencerRWood/homelab/issues/21)
was updated on 2026-10-11 at 11:03:17 UTC. It lists only the default Compose files,
omits the five media images and both Dockerfiles, and contains no open/pending
branches or lookup warnings. Its comments are empty. PR history contains 22
Renovate PRs, all merged, including initial pins
[PR #19](https://github.com/SpencerRWood/homelab/pull/19), Memcached
[PR #55](https://github.com/SpencerRWood/homelab/pull/55), and Calibre-Web
[PR #64](https://github.com/SpencerRWood/homelab/pull/64). There is no media update
PR in the collected history, nor a closed-unmerged Renovate PR suppressing one.
Generic initial-pin history is recorded here; per-image titled PRs are in JSON.

Historical hosted Mend execution logs and installation-level overrides were not
accessible through the available credentials/tools. Current local and full
GitHub dry-run logs provide extraction, lookup and replacement evidence; they
do not claim to reconstruct every historical hosted run. Successful public
registry resolution required no additional registry credentials or host rules.

## Configuration and policy

- `renovate.json` enables `docker-compose`, `dockerfile`, and `custom.regex`.
  Compose's existing default patterns are extended with `/^compose/.*\.ya?ml$/`.
  The three custom managers cover skipped image defaults, Caddy bases, and the
  specific LinuxServer mod. Tests and full dry-run file output verify ownership.
- Global digest pinning is retained and repeated in the Docker package rule
  because the regex manager defaults to `pinDigests: false`.
- Existing platform automerge, squash strategy, semantic commit conventions,
  and eligible image grouping remain. The broad eligible rule precedes manual
  exceptions. Detected major upgrades require manual review, and **every
  pgvector change** requires persistent-state and PostgreSQL compatibility review.
  Floating channels can contain upstream major changes that Docker versioning
  cannot classify; preserving those channels retains that existing limitation.
- Caddy's two base digests share one maintenance group. Their version updates
  are explicitly blocked; its local output name is excluded from registry lookup.
  `code-server-codex` is likewise excluded because it is built locally; its base
  is managed. These outputs must not be looked up on Docker Hub.
- `config:recommended` remains the only inherited preset. Its installed expansion
  includes the dashboard, ignored modules/tests, recommended groups, replacements,
  workarounds and changelog helpers. None excludes current deployment files.
  There is no repository schedule or extra registry override. Default rate limits
  are 2 PRs/hour and 10 concurrent PRs; digest/pin updates have Renovate's normal
  scheduling exceptions. Rate limits do not explain dependencies absent from
  extraction. Hosted installation-level limits were not independently visible.

The environment example contains empty override contracts, not authoritative
image pins. Renovate manages **Git defaults**, not values supplied privately by
Infisical or the host. Nonempty `*_IMAGE_TAG`, OpenProject `TAG`, or `CADDY_VERSION`
overrides can supersede Git defaults and need separate operational reconciliation.
No runtime secret values were read or written. Caddy's version is declared in
the Dockerfile ARG and Compose build/image/environment defaults; changing it
requires coordinating those locations and both variant digests.

## Validation and lifecycle

Renovate `44.151.2`, supported Node 24, and RE2 were used. Strict configuration
validation passes. The full GitHub dry run resolves all dependencies and prepares
two prospective branches: `renovate/depname-image-update` for normal initial pins
(10 files) and `renovate/caddy-image-update` for both Caddy base pins (one file).
No branch, commit, PR, issue or runtime service is mutated by these dry runs.
The final dry run has no lookup/configuration/replacement failure. Its only
warning concerns the default author identity of the audit CLI; it is not a hosted
Renovate authentication failure. Direct manifest checks independently resolve
all 24 external image/channel references and confirm the eight existing pins.

`.pre-commit-config.yaml` adds an always-run hook with isolated Node `24.11.0` and
`renovate@44.151.2`. `scripts/validate-renovate-coverage` runs strict validation
and `scripts/test-renovate-coverage.mjs` imports that exact Renovate installation.
Regression tests exercise real extraction, pin insertion, digest refresh,
version replacement, repeated references, variables and braces, mod pinning,
Caddy suffix/pin preservation, file matching, manager overlap, and manual rules.
Repository pre-commit validation, Ansible checks, existing unit/health/rollback
tests, and non-mutating Compose validation pass. The declared isolated weekly
recovery verification passes; its credentialed/live-host phases remain explicitly
not applicable. Initial sandbox-restricted verification failed; the authorized
isolated rerun outside that restriction passed and is the final evidence.

The active [Protect main ruleset](https://github.com/SpencerRWood/homelab/rules/23876719)
requires a PR and strict `validation / validation` status from GitHub Actions.
It has no bypass actors and reports that the current user cannot bypass it.
Renovate PR #64 passed that check before platform squash automerge. Digest PRs
therefore follow the existing required validation gate; this PR does not change
branch protection. The new regression hook runs within that existing required
validation job, without adding publication authority.

The release and deployment workflows are separately approval-gated manual
dispatches from `main`. PR merge does not publish or deploy. NAS mount gates,
sequential startup, `restart: "no"`, volumes, health checks, Ansible ownership,
rollback, and all runtime service definitions are unchanged.

## Exclusions and follow-up

- `local/caddy-cloudflare` and `code-server-codex`: local build outputs; maintain
  upstream bases instead of querying registries for these names.
- `pgvector/pgvector:0.8.2-pg16-bookworm` at `docs/postgres-migration.md:16` and
  `:37`: historical migration evidence, not a deployment selector. Changelog
  entries and synthetic regression examples are evidence/fixtures, not additional
  deployment sources. Removed Overleaf/Mongo/Redis definitions are not present
  at this fetched revision and are outside the current inventory.
- Review and merge this configuration PR after required CI. Let hosted Renovate
  generate normal pin PRs; the dry run's 16 missing pins are not manually included
  here. After those merge, verify a hosted dashboard/run shows all expected
  dependencies and inspect any registry failures before treating them as healthy.
- Caddy version upgrades remain blocked even after digest pins merge. A separate
  reviewed build-contract change must preserve the shared override, coordinate
  both variant digests, and demonstrate a successful full replacement dry run
  before re-enabling version updates. `2.11.7` is the known available patch at
  this audit snapshot, not an instruction to upgrade or deploy it.
- Reconcile private image overrides at a separately authorized operational
  boundary. Approve publication and deployment separately, then attest the
  released revision, effective image digests, deployment and runtime health.

This is trunk-based infrastructure/configuration work. Base and PR target are
fetched `main`; no OpenProject Story or release was assigned, so release association
is not applicable. The isolated branch is `fix/renovate-image-coverage-20261012`.
Full diagnostics remain in the local audit evidence directory; a sanitized
findings report and full structured matrix are saved to the established Drive
Logs folder. The PR and Drive links are supplied in the completion report.

## Sources

- [Renovate Compose discovery](https://docs.renovatebot.com/modules/manager/docker-compose/)
- [Renovate Dockerfile support](https://docs.renovatebot.com/modules/manager/dockerfile/)
- [Renovate regex managers](https://docs.renovatebot.com/modules/manager/regex/)
- [Non-mutating dry-run modes](https://docs.renovatebot.com/self-hosted-configuration/#dryrun)
- [LinuxServer mod loader digest syntax](https://github.com/linuxserver/docker-mods/blob/mod-scripts/docker-mods.v3#L299)

## Coverage matrix

| Service | Image / current reference | Every configuration source | Manager; discovered before → after | Pinned | Latest resolved digest | Update; policy; status |
| --- | --- | --- | --- | --- | --- | --- |
| calibre, ebook-importer | `lscr.io/linuxserver/calibre:latest@sha256:4b1673b28f18c170e8d6c48c791e67520df44dc4f9b9e8f63fef21d23910abab` | `compose/books/compose.yml:9`<br>`compose/books/compose.yml:95` | docker-compose; Yes → Yes | Yes | `sha256:4b1673b28f18c170e8d6c48c791e67520df44dc4f9b9e8f63fef21d23910abab` | No update in lookup; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
| calibre-web | `lscr.io/linuxserver/calibre-web:latest@sha256:5dcbcb381d29c4ccb2236910eb547679f482c3eb1c9e458138729e89eceb4774` | `compose/books/compose.yml:25` | docker-compose; Yes → Yes | Yes | `sha256:5dcbcb381d29c4ccb2236910eb547679f482c3eb1c9e458138729e89eceb4774` | No update in lookup; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
| calibre-web mod | `linuxserver/mods:universal-calibre` | `compose/books/compose.yml:30` | custom.regex; No → Yes | No | `sha256:de4c8d4b7d413cc9329742327b6e0ad5c12e2a855c5589c3492a62195dec975f` | Yes: pin; previous digest change unknown; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
| audiobookshelf | `ghcr.io/advplyr/audiobookshelf:2.37.1@sha256:581d68b2a6fc7ebf58d81c878a9f387cbbc0d88ac9d37b298b9cee10168af85b` | `compose/books/compose.yml:43` | docker-compose; Yes → Yes | Yes | `sha256:581d68b2a6fc7ebf58d81c878a9f387cbbc0d88ac9d37b298b9cee10168af85b` | No update in lookup; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
| bookshelf-audiobooks, bookshelf-ebooks | `ghcr.io/pennydreadful/bookshelf:softcover@sha256:23defe59522d0591ade31b2a59c674648f43be47fae769d93d32bb1e038c7170` | `compose/books/compose.yml:60`<br>`compose/books/compose.yml:77` | docker-compose; Yes → Yes | Yes | `sha256:23defe59522d0591ade31b2a59c674648f43be47fae769d93d32bb1e038c7170` | No update in lookup; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
| sonarr | `ghcr.io/hotio/sonarr:latest` | `compose/media/acquisition.yml:11` | docker-compose; No → Yes | No | `sha256:afc94d6134d3e21162bc86b82afee332c7555bedf4a29b710edcd794c9c38e1d` | Yes: pin; previous digest change unknown; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
| radarr | `ghcr.io/hotio/radarr:latest` | `compose/media/acquisition.yml:39` | docker-compose; No → Yes | No | `sha256:5de3a35527a4c4a9ec96be9a505cea6e775d705560abb7c27e230b005b3cdad7` | Yes: pin; previous digest change unknown; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
| sabnzbd | `lscr.io/linuxserver/sabnzbd:latest` | `compose/media/acquisition.yml:68` | docker-compose; No → Yes | No | `sha256:382f9bd4e3f6df2abf7bcc92edada0c5bd4d4ff26eb5416f257ac54989464fa1` | Yes: pin; previous digest change unknown; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
| prowlarr | `ghcr.io/hotio/prowlarr:latest` | `compose/media/acquisition.yml:97` | docker-compose; No → Yes | No | `sha256:ed37728f55a3e1f1049600ffcae4f266b83bcc804546963a9fdbea9a31d89c48` | Yes: pin; previous digest change unknown; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
| plex | `linuxserver/plex:latest` | `compose/media/plex.yml:9` | docker-compose; No → Yes | No | `sha256:06e07af2851e6a822e89062b148435495dd794d6d5aaf36247dee05fb3dcc4b8` | Yes: pin; previous digest change unknown; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
| caddy | `local/caddy-cloudflare:2.11.2` | `compose/platform/caddy/compose.yml:12` | Excluded (local build); No → No | No | N/A | Not applicable; Not applicable; **Excluded** |
| code-server-init, vikunja-init | `busybox:1.38@sha256:fd7dc98638c8e305f4dc34e979f1c0fdfdcaeb0fbf8fcff77ae834b6da3d7e6e` | `compose/platform/code-server/compose.yml:6`<br>`compose/productivity/vikunja/compose.yml:6` | docker-compose; Yes → Yes | Yes | `sha256:fd7dc98638c8e305f4dc34e979f1c0fdfdcaeb0fbf8fcff77ae834b6da3d7e6e` | No update in lookup; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
| code-server | `code-server-codex:latest` | `compose/platform/code-server/compose.yml:20` | Excluded (local build); No → No | No | N/A | Not applicable; Not applicable; **Excluded** |
| loki | `grafana/loki:latest` | `compose/platform/logging/compose.yml:6` | custom.regex; No → Yes | No | `sha256:1107dd5274e0ada47e42472b7a7e71f3b2a2fe878878108f3e2f9e51528f0193` | Yes: pin; previous digest change unknown; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
| grafana | `grafana/grafana:latest` | `compose/platform/logging/compose.yml:17` | custom.regex; No → Yes | No | `sha256:b28bae15e219c998fb0e0424ed724930cc61b1f61fb404d47c862f9a23f9e572` | Yes: pin; previous digest change unknown; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
| alloy | `grafana/alloy:latest` | `compose/platform/logging/compose.yml:48` | custom.regex; No → Yes | No | `sha256:2aa2099af76c0098d4af7a4d6e48f86cb66dc1a000222ad927a1c67c6542d13f` | Yes: pin; previous digest change unknown; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
| vaultwarden | `vaultwarden/server:latest` | `compose/platform/vaultwarden/compose.yml:8` | custom.regex; No → Yes | No | `sha256:efb3cde962015fcc036b2ea625242248611943b27212ebf4392841fb30fad055` | Yes: pin; previous digest change unknown; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
| postgres | `pgvector/pgvector:0.8.7-pg16-bookworm@sha256:7b822b0aac60967beb1ea5e576b8602c94c300a157d187f385ae3e0da199b90a` | `compose/postgres/compose.yml:7` | docker-compose; Yes → Yes | Yes | `sha256:7b822b0aac60967beb1ea5e576b8602c94c300a157d187f385ae3e0da199b90a` | No update in lookup; Manual review for every update; **Covered** |
| projects-cache | `memcached:1.6@sha256:2046d6d2eb7cbd59470b533a101cbd67def3e718b04eb72478306dbc804a3171` | `compose/productivity/openproject/compose.yml:22` | docker-compose; Yes → Yes | Yes | `sha256:2046d6d2eb7cbd59470b533a101cbd67def3e718b04eb72478306dbc804a3171` | No update in lookup; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
| projects-seeder, projects-web, projects-worker, projects-cron | `openproject/openproject:17-slim` | `compose/productivity/openproject/compose.yml:27`<br>`compose/productivity/openproject/compose.yml:45`<br>`compose/productivity/openproject/compose.yml:78`<br>`compose/productivity/openproject/compose.yml:90` | custom.regex; No → Yes | No | `sha256:2beeecac788d4f423c46a95ffbd04e6479491938b9924b610e9f47d81a38303c` | Yes: pin; previous digest change unknown; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
| projects-hocuspocus | `openproject/hocuspocus:17.9.1@sha256:2fb02a59609f5f197c7cedea1654d4cbcfc4e679e6fbc630f374d77e3448758e` | `compose/productivity/openproject/compose.yml:102` | docker-compose; Yes → Yes | Yes | `sha256:2fb02a59609f5f197c7cedea1654d4cbcfc4e679e6fbc630f374d77e3448758e` | No update in lookup; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
| mealie | `ghcr.io/mealie-recipes/mealie:latest` | `compose/productivity/recipes/compose.infisical.yml:8`<br>`compose/productivity/recipes/compose.yml:8` | custom.regex; No → Yes | No | `sha256:8b02290f4d1806f02acac6f25f6d48a3c965612fda1f8e914d5af533276f8688` | Yes: pin; previous digest change unknown; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
| vikunja | `vikunja/vikunja:latest` | `compose/productivity/vikunja/compose.yml:15` | custom.regex; No → Yes | No | `sha256:e2204a1c1c6a81e833c2b3a5442be182ca2335b54c2e7e37578cc3fe12a27cfc` | Yes: pin; previous digest change unknown; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
| Caddy base | `caddy:2.11.2-builder` | `compose/platform/caddy/Dockerfile:3` | custom.regex; No → Yes | No | `sha256:1ecefa333507828a592aaecc68d5f62a993787057429c04e9b0438a65c980a30` | Yes: pin available; 2.11.7 tag upgrade blocked; Automerge digest maintenance; version changes blocked; **Blocked** |
| Caddy base | `caddy:2.11.2-alpine` | `compose/platform/caddy/Dockerfile:11` | custom.regex; No → Yes | No | `sha256:834468128c7696cec0ceea6172f7d692daf645ae51983ca76e39da54a97c570d` | Yes: pin available; 2.11.7 tag upgrade blocked; Automerge digest maintenance; version changes blocked; **Blocked** |
| code-server base | `codercom/code-server:latest` | `compose/platform/code-server/Dockerfile:1` | dockerfile; No → Yes | No | `sha256:72ab24b5680ee597dd647b30d82625752f40109b5f61bef90ffbf1ea1f02dbb8` | Yes: pin; previous digest change unknown; Automerge eligible pins/digests/minor/patch; major manual; **Covered** |
