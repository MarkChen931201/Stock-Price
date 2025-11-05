#!/usr/bin/env sh
set -eu
DOMAIN="$CERTBOT_DOMAIN"
SUBDOMAIN="${DOMAIN%.duckdns.org}"
SUBDOMAIN="${SUBDOMAIN%%.*}"
TOKEN="${DUCKDNS_TOKEN:?DUCKDNS_TOKEN not set}"

printf "[duckdns-cleanup] Clearing TXT for _acme-challenge.%s\n" "$DOMAIN"
URL="https://www.duckdns.org/update?domains=${SUBDOMAIN}&token=${TOKEN}&txt=&clear=true"
if command -v curl >/dev/null 2>&1; then
  curl -fsS "$URL" || exit 1
else
  wget -qO- "$URL" || exit 1
fi
