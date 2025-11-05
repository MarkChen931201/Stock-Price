#!/usr/bin/env sh
set -eu
# Manual DNS auth hook for DuckDNS
# Requires DUCKDNS_TOKEN in env and CERTBOT_DOMAIN/CERTBOT_VALIDATION from certbot
DOMAIN="$CERTBOT_DOMAIN"
# Expect domain like stockprice.duckdns.org -> subdomain is the first label
SUBDOMAIN="${DOMAIN%.duckdns.org}"
# In case someone passes full domain with extra dots, keep the leftmost label only
SUBDOMAIN="${SUBDOMAIN%%.*}"
TOKEN="${DUCKDNS_TOKEN:?DUCKDNS_TOKEN not set}"
TXT_VALUE="$CERTBOT_VALIDATION"

printf "[duckdns-auth] Setting TXT for _acme-challenge.%s -> %s\n" "$DOMAIN" "$TXT_VALUE"
URL="https://www.duckdns.org/update?domains=${SUBDOMAIN}&token=${TOKEN}&txt=${TXT_VALUE}"
# Use curl if available, fallback to wget
if command -v curl >/dev/null 2>&1; then
  curl -fsS "$URL" || exit 1
else
  wget -qO- "$URL" || exit 1
fi
# Give DNS some time to propagate
sleep 30
