# Canonical books Compose migration

`compose/books/compose.yml` is the Git-managed definition for Calibre, Calibre-Web,
Audiobookshelf, bookshelf-audiobooks, bookshelf-ebooks, and ebook-importer. Ansible
deploys it to `/srv/homelab/compose/books/compose.yml`.

The cutover retained project identity `media-acquisition`, its shared external
`media-acquisition_media-network`, and the external `proxy` network. This permits the
books services to coexist with the separately canonical Sonarr, Radarr, SABnzbd, and
Prowlarr services without changing either network.

The ebook importer was the only service with an anonymous volume: its `/config` mount
is the existing external Docker volume
`5c22ba6009ba9e53444afb615fed0e154b0f453c5132bd7633202875d6998a4a`. The volume is
declared external and was reused directly; no state was copied, moved, or recreated.

All six book services were force-recreated once during the attended cutover so Docker
Compose labels now point to the canonical file. Their original images, bind mounts,
networks, container names, and `unless-stopped` restart policies are preserved. The
five media services were not affected.

The legacy `/srv/docker/media-acquisition/docker-compose.yml` remains a rollback
artifact. To roll back, run its existing Compose file for only the six book services;
do not remove the shared network or the importer volume.
