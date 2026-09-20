# Books stack

This directory is the canonical Git-managed definition for Calibre, Calibre-Web,
Audiobookshelf, bookshelf-audiobooks, bookshelf-ebooks, and ebook-importer. Ansible
deploys it to `/srv/homelab/compose/books/compose.yml` without a server-side Git
checkout.

The existing `media-acquisition` project identity and the shared
`media-acquisition_media-network` are retained. The network and `proxy` are declared
external so this canonical file does not alter them or the separately canonical media
services that share the project identity.

The ebook importer's historical anonymous `/config` volume is explicitly declared as
an external volume. Its data is not copied or moved. All other application state remains
at the audited bind paths under `/srv/docker` and `/mnt/wood-server-nas/media`.

The book services retain their existing `unless-stopped` restart policies. This feature
does not add a systemd startup model or alter their current Docker-managed boot behavior.
The legacy `/srv/docker/media-acquisition/docker-compose.yml` remains a rollback artifact.

Validate locally with:

```bash
docker compose -f compose/books/compose.yml config
```
