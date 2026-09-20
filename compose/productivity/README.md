# Productivity stack

This directory is the canonical Git-managed Compose ownership boundary for Mealie,
Vikunja, OpenProject, and Overleaf. Each application has a separate payload directory
to retain its existing Docker project identity, named volume names, and default-network
identity. Ansible deploys these files under `/srv/homelab/compose/productivity/`.

Render and operate each stack with `/srv/homelab/secrets/homelab.env`; values are never
committed. Existing `/srv/docker` paths remain the source of persistent state and
rollback artifacts. The Overleaf deployment is intentionally fresh following approved
removal of its prior state; its new state uses the same audited legacy path names.

The former Wiki service remains decommissioned and excluded.
