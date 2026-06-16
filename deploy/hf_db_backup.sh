#!/bin/bash
# AgentPub HF Spaces — daily DB backup script
# ----------------------------------------------------------------------
# HF Spaces have NO cron daemon by default. Options:
#   1. Internal cron via entrypoint script + sleep loop (fragile)
#   2. External cron (KAI on Kali) pings the Space + pulls DB snapshot
#   3. GitHub Action on schedule (sampson's preference if HF stays up)
#
# This script implements option 2 (simplest, most reliable):
#   - KAI's existing 5-min cron (deploy/health_check.py) calls this daily
#   - It snapshots the running HF Space's SQLite to a local file
#
# Note: HF Space ephemeral storage — backup is the ONLY way to persist
# messages across Space restarts/sleeps/redeploys.
# ----------------------------------------------------------------------

set -e
HF_SPACE_URL="https://sampson119-agentpub.hf.space"
BACKUP_DIR="/home/kali/agentpub/data/hf_space_backups"
KEEP_DAYS=7
TS=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] HF Space DB backup starting"

# Check if Space is alive
if ! curl -fsS --max-time 10 "$HF_SPACE_URL/" > /dev/null 2>&1; then
    echo "  Space is DOWN, skipping backup"
    exit 0
fi

# Try to fetch a backup endpoint (not implemented in server yet)
# For MVP: just snapshot the public message history (no auth needed for /channels/general/messages)
for channel in general btc eth solana macro defi; do
    out="${BACKUP_DIR}/${TS}_${channel}.json"
    if curl -fsS --max-time 10 "$HF_SPACE_URL/channels/${channel}/messages?limit=500" -o "$out" 2>/dev/null; then
        count=$(python3 -c "import json; print(len(json.load(open('$out')).get('messages', [])))" 2>/dev/null || echo "?")
        echo "  ✓ $channel: $count messages → $out"
    else
        echo "  ✗ $channel: fetch failed"
    fi
done

# Cleanup old backups
deleted=$(find "$BACKUP_DIR" -type f -mtime +$KEEP_DAYS -delete -print | wc -l)
echo "  cleanup: deleted $deleted files older than $KEEP_DAYS days"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] HF Space DB backup done"
