#!/usr/bin/env bash
# AgentPub — database snapshot.
#
# Takes a consistent SQLite backup using the online backup API (safe while
# the server is writing) and keeps the last 14 daily copies.
#
# Cron entry, installed by install.sh:
#   23 3 * * * root /opt/agentpub/deploy-backup.sh >> /var/log/agentpub-backup.log 2>&1
set -euo pipefail

APP_DIR="${AGENTPUB_APP_DIR:-/opt/agentpub}"
DATA_DIR="${AGENTPUB_DATA_DIR:-/var/lib/agentpub}"
BACKUP_DIR="${AGENTPUB_BACKUP_DIR:-/var/backups/agentpub}"
KEEP="${AGENTPUB_BACKUP_KEEP:-14}"

PYTHON="$APP_DIR/venv/bin/python"
DB="$DATA_DIR/agentpub.db"
[ -x "$PYTHON" ] || PYTHON="$(command -v python3)"
[ -f "$DB" ] || { echo "[agentpub] no database at $DB"; exit 0; }

mkdir -p "$BACKUP_DIR"
TS=$(date -u +%Y%m%dT%H%M%SZ)
TMP="$BACKUP_DIR/.snapshot-$TS.db"

# Consistent snapshot: the backup API copies page by page and handles WAL.
"$PYTHON" - "$DB" "$TMP" <<'PY'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1])
dst = sqlite3.connect(sys.argv[2])
src.backup(dst)
dst.close()
src.close()
PY

gzip -f "$TMP"
chmod 600 "$TMP.gz"
mv "$TMP.gz" "$BACKUP_DIR/agentpub-$TS.db.gz"

# prune old snapshots, newest first
ls -1t "$BACKUP_DIR"/agentpub-*.db.gz 2>/dev/null | tail -n "+$((KEEP + 1))" | while read -r old; do
  rm -f "$old"
done

echo "[agentpub] snapshot: $BACKUP_DIR/agentpub-$TS.db.gz"
