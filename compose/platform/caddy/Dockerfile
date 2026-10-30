ARG CADDY_VERSION=2.11.7

FROM caddy:${CADDY_VERSION}-builder@sha256:c4cd20eaa0b69112fd5d4f721ffc9671687e1d5d0b155c8620cf7546dbef94c0 AS builder

ARG CADDY_VERSION

WORKDIR /src
COPY modules/caddy-dns-cloudflare-patched /src/modules/caddy-dns-cloudflare-patched

RUN xcaddy build "v${CADDY_VERSION}" \
    --with github.com/caddy-dns/cloudflare=./modules/caddy-dns-cloudflare-patched

FROM caddy:${CADDY_VERSION}-alpine@sha256:e70b164da81ef698b3ad19af799ea6086ce6d9e48ed4079eb9fe26f6fbf14ee5

ARG CADDY_VERSION
LABEL org.opencontainers.image.version=${CADDY_VERSION}

COPY --from=builder /src/caddy /usr/bin/caddy
