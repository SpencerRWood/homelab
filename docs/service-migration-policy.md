# Service migration policy

Completed Compose ownership cutovers preserved the audited images, bind paths,
named volumes, UID/GID, ports, networks, and application state unless a separate
attended database or secret-source migration was documented. The remaining staged
code-server and observability services require a new attended recreation review.

For future cutovers, avoid combining Compose ownership changes with image upgrades,
persistent-data relocation, permission normalization, ingress redesign, or database
engine upgrades. Verify a recovery path first. Preserve existing unusual service
UID/GID mappings unless a separate change is explicitly validated.
