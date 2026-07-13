#!/bin/bash
# AgentPub MCP publish monitor
# ----------------------------------------------------------------------
# Detects new MCP registry versions + sends sampson alerts via 2 channels:
#   1. AgentPub #general (kai-mcp-monitor agent_id)
#   2. Local file log: /home/kali/agentpub/logs/mcp_publish_alerts.log
#   3. (Optional) Discord webhook via DISCORD_WEBHOOK_URL env var
# ----------------------------------------------------------------------
# Schedule: every 5 min (set in cron via `crontab -e` or `hermes cronjob add`)
# Last-touch: 2026-06-15 by KAI
# ----------------------------------------------------------------------

set -e
SERVER_NAME="io.github.liboy119/agentpub"
REGISTRY="https://registry.modelcontextprotocol.io/v0.1/servers?search=${SERVER_NAME}"
LOG_DIR="/home/kali/agentpub/logs"
LOG_FILE="${LOG_DIR}/mcp_publish_alerts.log"
STATE_FILE="${LOG_DIR}/mcp_publish_state.json"
AGENTPUB_URL="wss://flavia-asphyxial-unfamiliarly.ngrok-free.dev"
ALERT_AGENT_ID="kai-mcp-monitor"

mkdir -p "$LOG_DIR"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log() { echo "[$(ts)] $*" | tee -a "$LOG_FILE"; }

# 1. Fetch current state
response=$(curl -s --max-time 10 "$REGISTRY" 2>/dev/null || echo '{"servers":[]}')
version=$(echo "$response" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    servers = d.get('servers', [])
    if not servers:
        print('NONE')
    else:
        s = servers[0]
        print(s.get('server', {}).get('version', 'NONE'))
except Exception as e:
    print('NONE')
" 2>/dev/null)

is_latest=$(echo "$response" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    s = d.get('servers', [{}])[0]
    meta = s.get('_meta', {}).get('io.modelcontextprotocol.registry/official', {})
    print('true' if meta.get('isLatest') else 'false')
except Exception:
    print('false')
" 2>/dev/null)

status=$(echo "$response" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    s = d.get('servers', [{}])[0]
    meta = s.get('_meta', {}).get('io.modelcontextprotocol.registry/official', {})
    print(meta.get('status', 'unknown'))
except Exception:
    print('unknown')
" 2>/dev/null)

# 2. Load previous state
prev_version="NONE"
if [ -f "$STATE_FILE" ]; then
    prev_version=$(python3 -c "
import json
try:
    with open('$STATE_FILE') as f:
        d = json.load(f)
    print(d.get('version', 'NONE'))
except Exception:
    print('NONE')
" 2>/dev/null || echo "NONE")
fi

# 3. Detect change
if [ "$version" != "$prev_version" ]; then
    log "🔄 MCP publish change detected: $prev_version → $version (status=$status isLatest=$is_latest)"

    # 3a. Update state file
    cat > "$STATE_FILE" <<EOF
{
  "version": "$version",
  "status": "$status",
  "is_latest": "$is_latest",
  "last_checked": "$(ts)"
}
EOF

    # 3b. Post to #general on AgentPub
    cd /home/kali/桌面/agent/agentpub
    /home/kali/桌面/agent/agentpub/.venv/bin/python -c "
import asyncio
from agentpub import AgentPub

async def alert():
    ap = AgentPub('$AGENTPUB_URL', '$ALERT_AGENT_ID')
    try:
        await ap.connect('general')
        msg = f'[MCP-MONITOR] New version: $version (was $prev_version). Status: $status. isLatest: $is_latest.'
        await ap.send(msg)
        print('  → posted to #general')
    except Exception as e:
        print(f'  → #general post failed: {e}')
    finally:
        try: await ap.close()
        except: pass

asyncio.run(alert())
" 2>&1 | tee -a "$LOG_FILE"

    # 3c. Optional Discord webhook (only if env var is set — sampson sets this on his side)
    if [ -n "$DISCORD_WEBHOOK_URL" ]; then
        log "  → sending Discord webhook"
        curl -s -X POST "$DISCORD_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"content\": \"🔄 AgentPub MCP registry version change: \`$prev_version\` → \`$version\` (status=$status isLatest=$is_latest)\"}" \
            --max-time 5 >> "$LOG_FILE" 2>&1 || log "  → Discord webhook failed"
    else
        log "  → Discord webhook skipped (DISCORD_WEBHOOK_URL not set)"
    fi
else
    # Quiet mode — only log if it's been a while since last check
    if [ ! -f "${LOG_FILE}.last_quiet" ] || [ $(($(date +%s) - $(stat -c %Y "${LOG_FILE}.last_quiet" 2>/dev/null || echo 0))) -gt 3600 ]; then
        log "  ✓ version=$version (no change)"
        touch "${LOG_FILE}.last_quiet"
    fi
fi
