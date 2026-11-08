#!/usr/bin/env bash
# Deploy one Render service at a specific commit and wait until it is live.
#
# Usage: RENDER_API_KEY=... scripts/render-deploy.sh <service-id> <commit-sha>
#
# Render switches traffic only after the new version passes its health check,
# so a failed deploy leaves the previous version serving. Exits non-zero unless
# the deploy reaches "live".
set -euo pipefail

service_id="$1"
commit="$2"
api="https://api.render.com/v1"
auth=(-H "Authorization: Bearer ${RENDER_API_KEY:?RENDER_API_KEY is required}" -H "Accept: application/json")

deploy=$(curl -fsS -X POST "${auth[@]}" -H "Content-Type: application/json" \
  -d "{\"commitId\": \"${commit}\"}" "${api}/services/${service_id}/deploys")
deploy_id=$(echo "$deploy" | jq -r '.id')
echo "Started deploy ${deploy_id} of ${commit} to ${service_id}"

for _ in $(seq 1 90); do  # up to ~15 minutes (free builds can be slow)
  status=$(curl -fsS "${auth[@]}" "${api}/services/${service_id}/deploys/${deploy_id}" | jq -r '.status')
  case "$status" in
    live) echo "Deploy ${deploy_id} is live"; exit 0 ;;
    build_failed|update_failed|canceled|deactivated|pre_deploy_failed)
      echo "Deploy ${deploy_id} ended with status ${status}; the previous version keeps serving" >&2
      exit 1 ;;
  esac
  sleep 10
done
echo "Timed out waiting for deploy ${deploy_id} (last status: ${status})" >&2
exit 1
