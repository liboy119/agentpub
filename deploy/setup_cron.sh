#!/bin/bash
# AgentPub health check cron installer
# One-shot: registers a */5 min health check in current user's crontab.
# Idempotent: safe to re-run.

set -e

SCRIPT_PATH="/home/kali/桌面/agent/agentpub/deploy/health_check.py"
LOG_PATH="/home/kali/桌面/agent/agentpub/logs/health_check.log"
CRON_LINE="*/5 * * * * $SCRIPT_PATH >> $LOG_PATH 2>&1  # agentpub-health"

if [ ! -x "$SCRIPT_PATH" ]; then
    echo "ERROR: $SCRIPT_PATH not executable. Run: chmod +x $SCRIPT_PATH"
    exit 1
fi

# Ensure log dir exists
mkdir -p "$(dirname "$LOG_PATH")"

# Read current crontab
CURRENT=$(crontab -l 2>/dev/null || true)

if echo "$CURRENT" | grep -qF "$SCRIPT_PATH"; then
    echo "✅ already registered:"
    echo "$CURRENT" | grep -F "$SCRIPT_PATH"
    exit 0
fi

# Append
( echo "$CURRENT"; echo "$CRON_LINE" ) | crontab -

echo "✅ Installed:"
crontab -l | grep -F "$SCRIPT_PATH"

echo ""
echo "Test now (will print result + write to log):"
echo "  $SCRIPT_PATH"
