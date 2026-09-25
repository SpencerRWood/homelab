# CHANGELOG

<!-- version list -->

## v0.17.1 (2026-09-25)

### Bug Fixes

- **deploy**: Apply pinned Calibre images in release path
  ([`4f71ca5`](https://github.com/SpencerRWood/homelab/commit/4f71ca59dc45335edf21489110e25664295432a8))


## v0.17.0 (2026-09-25)

### Features

- **secrets**: Migrate homelab postgres to Infisical
  ([`84ad51a`](https://github.com/SpencerRWood/homelab/commit/84ad51a999cb0f6ef4225743d807e3d1f4de9baf))


## v0.16.0 (2026-09-25)

### Chores

- **deps**: Update lscr.io/linuxserver/calibre:latest docker digest to 84d3e30
  ([#35](https://github.com/SpencerRWood/homelab/pull/35),
  [`6900b79`](https://github.com/SpencerRWood/homelab/commit/6900b79bd700a39eba2d63dac87e28e0da1294f7))

### Features

- **secrets**: Migrate Caddy and Vaultwarden to Infisical
  ([`5e502c7`](https://github.com/SpencerRWood/homelab/commit/5e502c77e94ae7bfb287b7cd1353c2bd0309319e))


## v0.15.0 (2026-09-25)

### Bug Fixes

- **mealie**: Resolve scoped Infisical export safely
  ([`86ef48c`](https://github.com/SpencerRWood/homelab/commit/86ef48c9717d42a1a9492a61f41b6503cb96d8e4))

### Features

- **mealie**: Prepare scoped Infisical canary deployment
  ([`10ba5e8`](https://github.com/SpencerRWood/homelab/commit/10ba5e8f54ddf33aa64ac3fa44611f24c2fa7114))

- **secrets**: Deploy homelab services through Infisical
  ([`74bc6b4`](https://github.com/SpencerRWood/homelab/commit/74bc6b408935556d20f10600139e504806740829))


## v0.14.13 (2026-09-23)

### Chores

- **deps**: Update memcached:1.6 docker digest to 405a445
  ([#30](https://github.com/SpencerRWood/homelab/pull/30),
  [`e7e6097`](https://github.com/SpencerRWood/homelab/commit/e7e6097f6a07254e2823e7ae725b16c7b7ff39e5))


## v0.14.12 (2026-09-23)

### Chores

- **deps**: Update busybox:1.38 docker digest to fd7dc98
  ([#28](https://github.com/SpencerRWood/homelab/pull/28),
  [`d548b39`](https://github.com/SpencerRWood/homelab/commit/d548b3926cc4a6c4db7a8438506b09c547f51594))


## v0.14.11 (2026-09-23)

### Chores

- **deps**: Update openproject/hocuspocus docker tag to v17.8.0
  ([#27](https://github.com/SpencerRWood/homelab/pull/27),
  [`65db56d`](https://github.com/SpencerRWood/homelab/commit/65db56d40c6dd74fc200bcc48b99a2a19f56abfc))


## v0.14.10 (2026-09-23)

### Chores

- **deps**: Update ghcr.io/advplyr/audiobookshelf docker tag to v2.36.1
  ([#24](https://github.com/SpencerRWood/homelab/pull/24),
  [`6c49ebc`](https://github.com/SpencerRWood/homelab/commit/6c49ebc57b245f935197213dbcd498e1e4c4e42e))


## v0.14.9 (2026-09-23)

### Chores

- **deps**: Update busybox docker tag to v1.38
  ([#23](https://github.com/SpencerRWood/homelab/pull/23),
  [`b803c13`](https://github.com/SpencerRWood/homelab/commit/b803c13d1563e82edc0420245785414425059e1d))


## v0.14.8 (2026-09-22)

### Chores

- **deps**: Update pgvector/pgvector docker tag to v0.8.6
  ([#20](https://github.com/SpencerRWood/homelab/pull/20),
  [`dea8925`](https://github.com/SpencerRWood/homelab/commit/dea8925aef8c29b96eae0c613203d8e35f511f8e))


## v0.14.7 (2026-09-22)

### Bug Fixes

- **release**: Deploy Renovate dependency patches
  ([`02e24d3`](https://github.com/SpencerRWood/homelab/commit/02e24d35f9540fde82f8d78ebbb2433ce0db5f96))

### Chores

- **deps**: Pin dependencies ([#19](https://github.com/SpencerRWood/homelab/pull/19),
  [`0a3dc90`](https://github.com/SpencerRWood/homelab/commit/0a3dc903850db645cefa9c4bc3709df160c4fa7f))


## v0.14.6 (2026-09-22)

### Bug Fixes

- **ci**: Allow immutable image references
  ([`2ac5cab`](https://github.com/SpencerRWood/homelab/commit/2ac5cabf383fe52b5dd3961907a58c98067753b3))


## v0.14.5 (2026-09-22)

### Bug Fixes

- **ci**: Validate pull requests
  ([`71e073b`](https://github.com/SpencerRWood/homelab/commit/71e073b1890007d206854c2981cda1c79c9aed52))


## v0.14.4 (2026-09-22)

### Bug Fixes

- Run homelab health checks without uv
  ([`f270694`](https://github.com/SpencerRWood/homelab/commit/f2706948c65ce1c760997eacfdf700f114d93ad4))


## v0.14.3 (2026-09-22)

### Bug Fixes

- Refresh APT cache only for runner bootstrap
  ([`3556166`](https://github.com/SpencerRWood/homelab/commit/3556166ef12f3bad68f51118e3240b16f59c34dd))


## v0.14.2 (2026-09-22)

### Bug Fixes

- Run homelab deployment Ansible locally
  ([`455be07`](https://github.com/SpencerRWood/homelab/commit/455be0711215b33885aad53e8ade1d5e791a8cb4))


## v0.14.1 (2026-09-22)

### Bug Fixes

- Treat homelab secrets as Compose env data
  ([`71a50a5`](https://github.com/SpencerRWood/homelab/commit/71a50a5d6f5173e5c5bed950ca82523ccb9d95b2))


## v0.14.0 (2026-09-22)

### Bug Fixes

- Use compatible deployment workflow contract
  ([`ff9545d`](https://github.com/SpencerRWood/homelab/commit/ff9545dd3764a8854360966f182a467667e64809))

### Features

- Provision isolated Beelink homelab runner ([#13](https://github.com/SpencerRWood/homelab/pull/13),
  [`5029ef7`](https://github.com/SpencerRWood/homelab/commit/5029ef7e1986854ed5b1f03b7879e0267c12aa80))


## v0.13.4 (2026-09-21)

### Bug Fixes

- Run homelab health checks as remote script
  ([`45eaf62`](https://github.com/SpencerRWood/homelab/commit/45eaf62105256e085f6607680bd1e44302d562b2))


## v0.13.3 (2026-09-21)

### Bug Fixes

- Avoid templating in container health checks
  ([`1fed3d3`](https://github.com/SpencerRWood/homelab/commit/1fed3d3a6472a3f94361ec1c5d9d5c127f28ffc3))


## v0.13.2 (2026-09-21)

### Bug Fixes

- Escape Docker templates in health checks
  ([`cad4ec0`](https://github.com/SpencerRWood/homelab/commit/cad4ec0e33223dcde668367cc8f9d0c619645cff))


## v0.13.1 (2026-09-21)

### Bug Fixes

- Run deployment Ansible through uv
  ([`14c96f5`](https://github.com/SpencerRWood/homelab/commit/14c96f56e3aae14c9fefc458a79a08e094b9d08d))


## v0.13.0 (2026-09-21)

### Bug Fixes

- **ci**: Satisfy deployment workflow validation
  ([`ce1c246`](https://github.com/SpencerRWood/homelab/commit/ce1c246ec0015994474b51a7bb80171b46f86cfb))

### Features

- Deploy released homelab configuration
  ([`9d9cb1a`](https://github.com/SpencerRWood/homelab/commit/9d9cb1a46fd09e62865ae39d703364370f206d10))


## v0.12.0 (2026-09-21)

### Features

- Migrate grafana database to homelab postgres
  ([`1a9333d`](https://github.com/SpencerRWood/homelab/commit/1a9333dcf9190563fb8a24cdbee3d3c6b7821843))


## v0.11.0 (2026-09-21)

### Features

- Migrate remaining homelab services to postgres
  ([`edd33e8`](https://github.com/SpencerRWood/homelab/commit/edd33e8f09a3732f97bfe8aa982623d16ae64721))


## v0.10.0 (2026-09-21)

### Features

- Migrate mealie to homelab postgres
  ([`c69ab4d`](https://github.com/SpencerRWood/homelab/commit/c69ab4d9c7a11290b30bd3dd59e5cd2f991acf09))


## v0.9.1 (2026-09-21)

### Bug Fixes

- Require postgres bootstrap secrets
  ([`c08b766`](https://github.com/SpencerRWood/homelab/commit/c08b766e3b2a1768d1f996c0f8c408c339ee5e75))


## v0.9.0 (2026-09-21)

### Features

- Add dedicated homelab postgres
  ([`fafa7fb`](https://github.com/SpencerRWood/homelab/commit/fafa7fb5d0c73497e2fef14baf95cc6b332c9cd5))


## v0.8.0 (2026-09-21)

### Features

- Migrate caddy to canonical compose
  ([`600c115`](https://github.com/SpencerRWood/homelab/commit/600c1156da9006fdef86c20678d93f12481eba40))


## v0.7.0 (2026-09-21)

### Features

- Add canonical platform compose payloads
  ([`a9fb1a6`](https://github.com/SpencerRWood/homelab/commit/a9fb1a6d284b2925df843fe165b103b863fe0dbd))


## v0.6.0 (2026-09-20)

### Features

- Migrate productivity services to canonical Compose
  ([`8f053ad`](https://github.com/SpencerRWood/homelab/commit/8f053ad2672ca6755b71c8e64c875327a66cb429))


## v0.5.0 (2026-09-20)

### Features

- Migrate books services to canonical Compose
  ([`2bce930`](https://github.com/SpencerRWood/homelab/commit/2bce930dcf25ba806817dad83cba1eceb3e0f0f4))


## v0.4.0 (2026-09-20)

### Features

- Migrate media services to canonical Compose
  ([`4187637`](https://github.com/SpencerRWood/homelab/commit/418763714b81cb56a09db352de0a625642b0e42f))


## v0.3.0 (2026-09-20)

### Features

- Gate media startup on NAS storage
  ([`dd19c6e`](https://github.com/SpencerRWood/homelab/commit/dd19c6eecb695a378808705e156948382d41aa73))


## v0.2.1 (2026-09-20)

### Bug Fixes

- Format storage fstab backup filename
  ([`d3af6c2`](https://github.com/SpencerRWood/homelab/commit/d3af6c241d92b7bc7f57e29cff822cbd363d482d))


## v0.2.0 (2026-09-20)

### Features

- Manage Beelink NFS mounts with Ansible
  ([`ea40150`](https://github.com/SpencerRWood/homelab/commit/ea40150485b8dd7750fb5da754b9d2ad9d4d780f))


## v0.1.0 (2026-09-20)

- Initial Release
