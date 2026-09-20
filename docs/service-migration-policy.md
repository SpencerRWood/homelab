# Service migration policy

Every initial service migration preserves its current image/tag, bind paths, named
volumes, UID/GID, ports, networks, configuration sources, and database dependencies.

It must not also introduce image upgrades, persistent-data relocation, permission
normalization, ingress redesign, or database-engine upgrades. Each service needs a
tested rollback path before migration. Existing unusual service UID/GID mappings from
the audit must be preserved, not silently normalized.
