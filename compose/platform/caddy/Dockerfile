ARG CADDY_VERSION=2.11.7

FROM caddy:${CADDY_VERSION}-builder@sha256:d842facfd63b960922e57444ff76fd8f0793a66dfdcf481af8026e1f4e6a39b4 AS builder

ARG CADDY_VERSION

WORKDIR /src
COPY modules/caddy-dns-cloudflare-patched /src/modules/caddy-dns-cloudflare-patched

RUN xcaddy build "v${CADDY_VERSION}" \
    --with github.com/caddy-dns/cloudflare=./modules/caddy-dns-cloudflare-patched

FROM caddy:${CADDY_VERSION}-alpine@sha256:d8542f48d34a9cf4e4c11a478865229840e87e4c96ea3f439101f31a5d35f75f

ARG CADDY_VERSION
LABEL org.opencontainers.image.version=${CADDY_VERSION}

COPY --from=builder /src/caddy /usr/bin/caddy
