# Repository Guidance

## Purpose and boundaries
- Own home-only host configuration and service definitions; portable platform components belong in `infrastructure`.
- Keep Git as the source of truth. The managed host is a deployment target, not an authoritative checkout.

## Development
- Use `ansible/` for host configuration and `compose/` for home service lifecycle; follow `docs/architecture.md` for ownership.
- Keep environment inputs outside Git and use the examples only as contracts.

## Validation
- Run `uv run pre-commit run --all-files` for repository checks.
- For Ansible changes, use `uv run ansible-playbook ansible/playbooks/homelab-host.yml --syntax-check`.
- For a changed stack, run `docker compose -f <changed-compose-file> config` with required local environment inputs.

## Architecture constraints
- Preserve the boundary between host prerequisites and Compose-managed services.
- Keep home and portable environment configuration separate.

## Safety
- Review storage, mount, backup, and rollback behavior before changing persistent state or startup order.
- Never commit resolved environment files or service credentials.

## Branching strategy

- This repository uses **trunk-based development**. Create short-lived change branches from current `main` and target PRs to `main`.
- Follow the [canonical branching and delivery policy](https://github.com/SpencerRWood/codex-config/blob/main/docs/branching-policy.md), available through the installed codex-config source path. Verify the strategy, release association, fetched base and PR target before implementation and record them in Story evidence. Story completion does not authorize publication or deployment; retain existing review, CI, security and rollback requirements.
