#!/usr/bin/env bash
# AgentPub — deploy or update.
#
#   ./deploy/deploy.sh            build, restart, health check
#   ./deploy/deploy.sh --fresh    wipe the database and start clean
#
# Safe to run repeatedly. Takes a snapshot of the database before replacing it.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

FRESH=0
[ "${1:-}" = "--fresh" ] && FRESH=1

if [ ! -f .env ]; then
  echo "deploy/.env is missing — copy deploy/.env.example and fill it in" >&2
  exit 1
fi

echo "[agentpub] backing up the current database"
./backup.sh || echo "[agentpub] backup skipped"

if [ "$FRESH" -eq 1 ]; then
  echo "[agentpub] --fresh: removing the data volume"
  docker compose down
  docker volume rm agentpub_agentpub-data 2>/dev/null || true
fi

echo "[agentpub] building and restarting"
docker compose up -d --build

echo "[agentpub] waiting for health"
ok=0
for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:7701/healthz >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 2
done

if [ "$ok" -ne 1 ]; then
  echo "[agentpub] the API did not come up — recent logs:" >&2
  docker compose logs --tail 40 agentpub >&2
  exit 1
fi

PUBLIC_URL=$(grep '^AGENTPUB_PUBLIC_URL=' .env | cut -d= -f2-)
echo "[agentpub] health:"
curl -fsS "${PUBLIC_URL}/healthz" && echo
echo "[agentpub] deployed."
