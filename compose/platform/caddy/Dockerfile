ARG CADDY_VERSION=2.11.7

FROM caddy:${CADDY_VERSION}-builder@sha256:bf6a7d38add2508b7d2e3e3f40cf2af399214f143c0fa3daa51f254e01f8d293 AS builder

ARG CADDY_VERSION

WORKDIR /src
COPY modules/caddy-dns-cloudflare-patched /src/modules/caddy-dns-cloudflare-patched

RUN xcaddy build "v${CADDY_VERSION}" \
    --with github.com/caddy-dns/cloudflare=./modules/caddy-dns-cloudflare-patched

FROM caddy:${CADDY_VERSION}-alpine@sha256:eb4d35b7452d1ab6171fbdbe8d9275b2301dad6dad92115d91e19fb9b24d510f

ARG CADDY_VERSION
LABEL org.opencontainers.image.version=${CADDY_VERSION}

COPY --from=builder /src/caddy /usr/bin/caddy
