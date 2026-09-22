# Architecture

```text
GitHub Release -> github-runner-homelab (Beelink) -> Ansible -> homelab Compose/state
GitHub Release -> github-runner-infrastructure (Beelink) -> Ansible -> infrastructure-dev Compose/state
```

On the Beelink, Ansible currently manages adopted NAS mounts, canonical Compose payloads
and their server-side secret file, and mount-gated media startup. Host baseline,
users/groups, Docker, networking/security, and backup changes remain outside the current
implemented ownership boundary. Docker Compose then runs the media, books, platform,
and productivity services.

Terraform provisions cloud or otherwise provisionable infrastructure. Ansible configures
hosts. Docker Compose runs application services. The Beelink is a managed deployment
target, never the authoritative Git working copy.

## Release and deployment boundary

`main` releases are validated through `SpencerRWood/workflows@v1` and represent a
versioned declarative configuration state. The always-on Beelink intentionally hosts two
isolated GitHub Actions runners: this repository owns `github-runner-homelab`; the
infrastructure repository owns `github-runner-infrastructure`. They have separate Unix
accounts, GitHub registrations, labels, work directories, services, runner-local secrets,
and deployment metadata. The MacBook is not required for routine CI/CD execution.

A release workflow checks out the exact published tag on the matching runner, validates
the inventory, syntax, lint and Compose payload, then invokes its root-owned canonical
Ansible entrypoint. Health checks run afterward; a failure reapplies the prior successful
configuration release once. This is configuration rollback only, never a database rollback.
The intentional co-location of runner control plane and managed node favors availability
and unattended deployment over strict control-plane/node separation.
