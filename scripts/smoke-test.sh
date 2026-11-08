#!/usr/bin/env bash
# Post-deploy smoke test: the API health endpoint and the frontend respond.
# Free Render services may be asleep, so allow a cold start of a minute or two.
#
# Usage: scripts/smoke-test.sh <api-base-url> <frontend-url>
set -euo pipefail

api_url="${1%/}"
web_url="${2%/}"

for _ in $(seq 1 24); do
  if curl -fsS --max-time 20 "${api_url}/api/health" | grep -q '"ok"'; then
    echo "API healthy: ${api_url}"
    break
  fi
  sleep 5
done
curl -fsS --max-time 20 "${api_url}/api/health" | grep -q '"ok"'

curl -fsS --max-time 20 "${web_url}/" | grep -q 'pressure·point' && echo "Frontend up: ${web_url}"
