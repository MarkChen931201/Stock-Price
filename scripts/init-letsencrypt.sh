#!/usr/bin/env bash
set -euo pipefail

# One-time certificate issuance using webroot with Certbot.
# Requirements:
#   - docker compose up -d nginx (nginx must be serving port 80)
#   - .env file with DOMAIN and EMAIL variables, or export them in shell

DOMAIN=${DOMAIN:-}
EMAIL=${EMAIL:-}
if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
  echo "Please set DOMAIN and EMAIL environment variables."
  echo "Example: DOMAIN=myhome.duckdns.org EMAIL=you@example.com $0"
  exit 1
fi

echo "Issuing certificate for $DOMAIN ..."
docker compose run --rm \
  --entrypoint certbot \
  certbot certonly --webroot \
  -w /var/www/certbot \
  -d "$DOMAIN" \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email

echo "Certificate issued. Reloading nginx..."
docker compose exec nginx nginx -s reload || true
echo "Done."
