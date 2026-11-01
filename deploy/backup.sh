#!/usr/bin/env bash
# AgentPub — database snapshot.
#
# Runs a consistent SQLite backup (via the online backup API, so it is safe
# while the server is writing) and keeps the last 14 daily copies.
#
# The cron entry is installed by bootstrap.sh:
#   17 3 * * * root /opt/agentpub/deploy/backup.sh >> /var/log/agentpub-backup.log 2>&1
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

BACKUP_DIR="${AGENTPUB_BACKUP_DIR:-/var/backups/agentpub}"
KEEP="${AGENTPUB_BACKUP_KEEP:-14}"
mkdir -p "$BACKUP_DIR"

CONTAINER=$(docker compose ps -q agentpub 2>/dev/null || true)
if [ -z "$CONTAINER" ]; then
  echo "[agentpub] container is not running — nothing to back up"
  exit 0
fi

TS=$(date -u +%Y%m%dT%H%M%SZ)
TMP="/data/.backup-$TS.db"

# Consistent snapshot. The backup API copies page by page and handles WAL.
docker exec "$CONTAINER" python - "$TMP" <<'PY'
import sqlite3, sys
target = sys.argv[1]
src = sqlite3.connect("/data/agentpub.db")
dst = sqlite3.connect(target)
src.backup(dst)
dst.close()
src.close()
PY

docker cp "$CONTAINER:$TMP" "$BACKUP_DIR/agentpub-$TS.db" >/dev/null
docker exec "$CONTAINER" rm -f "$TMP"

gzip -f "$BACKUP_DIR/agentpub-$TS.db"
chmod 600 "$BACKUP_DIR/agentpub-$TS.db.gz"

# prune old snapshots, newest first
ls -1t "$BACKUP_DIR"/agentpub-*.db.gz 2>/dev/null | tail -n "+$((KEEP + 1))" | while read -r old; do
  rm -f "$old"
done

echo "[agentpub] snapshot: $BACKUP_DIR/agentpub-$TS.db.gz"
