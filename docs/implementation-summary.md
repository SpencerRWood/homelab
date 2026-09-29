# Implementation history

## Current state

The private `SpencerRWood/homelab` repository is the source of truth for Beelink
home-service definitions. The centralized release and deployment workflow is active.

The v0.2.x releases take declarative ownership of the three existing NFS mount records
while preserving their active runtime mounts. v0.3.0 adds
[`homelab-media.service`](media-startup.md), which owns mount-gated boot startup for
the selected media workloads. Its attended reboot validation passed.

## Subsequent cutovers

The canonical media and books Compose cutovers passed. The productivity cutover also
passed its attended reboot validation: Mealie, Vikunja, OpenProject, and a fresh
Overleaf stack returned with Caddy ingress intact. The Caddy canonical cutover passed
on 2026-09-21, preserving its `proxy` project identity, certificate volumes, and
legacy configuration binds. Grafana, Loki, Alloy, and code-server were intentionally
stopped on 2026-09-21 pending later recreation; their legacy runtime artifacts and
staged canonical payloads remain intact. The Vaultwarden canonical cutover passed on
2026-09-21, preserving its `/data` bind, image, network topology, and proxy reachability.
Persistent state normalization has not been implemented; existing state paths and
legacy Compose files remain recovery inputs. The current service classification is
in the [README](../README.md); detailed recovery contracts are in the
[ownership inventory](compose-ownership-migration-inventory.md).
