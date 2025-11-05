#!/usr/bin/env bash
set -euo pipefail

# DNS-01 issuance via DuckDNS API, no need to open ports 80/443.
# Prerequisites: .env has DUCKDNS_TOKEN, DOMAIN, EMAIL; compose services up so volumes exist.

DOMAIN=${DOMAIN:-}
EMAIL=${EMAIL:-}
DUCKDNS_TOKEN_ENV=${DUCKDNS_TOKEN:-}

if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
  echo "Please set DOMAIN and EMAIL environment variables."
  echo "Example: DOMAIN=stockprice.duckdns.org EMAIL=you@example.com $0"
  exit 1
fi

if [[ -z "$DUCKDNS_TOKEN_ENV" ]]; then
  echo "Please set DUCKDNS_TOKEN in your environment or .env file."
  exit 1
fi

echo "Requesting DNS-01 certificate for $DOMAIN via DuckDNS ..."
# Pass DUCKDNS_TOKEN into the container env; hooks mounted at /scripts
# -n non-interactive, agree-tos, and manual-public-ip-logging-ok to avoid prompts
# We use --preferred-challenges dns and manual hooks to set/clear TXT

docker compose run --rm \
  -e DUCKDNS_TOKEN="$DUCKDNS_TOKEN_ENV" \
  --entrypoint certbot \
  certbot certonly \
  --manual --preferred-challenges dns \
  --manual-auth-hook /scripts/duckdns-auth.sh \
  --manual-cleanup-hook /scripts/duckdns-cleanup.sh \
  -d "$DOMAIN" \
  -m "$EMAIL" \
  --agree-tos --no-eff-email -n

echo "Certificate request completed. Reloading nginx if present..."
docker compose exec nginx nginx -s reload || true
