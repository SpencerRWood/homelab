ARG CADDY_VERSION=2.11.7

FROM caddy:${CADDY_VERSION}-builder@sha256:671d2a6e5465cc894c9ca57706c7ea7d101018059fe3154c65805a0eda550467 AS builder

ARG CADDY_VERSION

WORKDIR /src
COPY modules/caddy-dns-cloudflare-patched /src/modules/caddy-dns-cloudflare-patched

RUN xcaddy build "v${CADDY_VERSION}" \
    --with github.com/caddy-dns/cloudflare=./modules/caddy-dns-cloudflare-patched

FROM caddy:${CADDY_VERSION}-alpine@sha256:24ec7b05bc532c7bb57f727030c5056e257ff7138b4b50460306819ff79362bd

ARG CADDY_VERSION
LABEL org.opencontainers.image.version=${CADDY_VERSION}

COPY --from=builder /src/caddy /usr/bin/caddy
