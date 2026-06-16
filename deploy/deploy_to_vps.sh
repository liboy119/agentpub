#!/usr/bin/env bash
# ⚠️ DEPRECATED 2026-06-16 — see docs/VPS_CANCELLED_2026-06-16.md
# AgentPub VPS deployment script — one-shot provisioning on a fresh Ubuntu/Debian VPS.
# NOT IN ACTIVE USE. sampson decision 6/16: cancel all VPS/Oracle/Hetzner work.
# Re-activation condition: 5 真 agent 上线 + sampson 拍板.
# This script is kept for historical reference only. DO NOT RUN.
#
# Pipeline (per sampson 6/15 plan — SUPERSEDED):
#   1. ssh root@$VPS_IP: apt install python3-pip python3-venv
#   2. scp -r . vps:/app/agentpub/
#   3. ssh vps: python3 -m venv /app/agentpub/.venv
#   4. ssh vps: /app/agentpub/.venv/bin/pip install -e /app/agentpub
#   5. ssh vps: write systemd service file
#   6. ssh vps: systemctl enable --now agentpub-server
#   7. verify: curl http://$VPS_IP:7700/
#
# Usage:
#   ./deploy/deploy_to_vps.sh                            # interactive prompts
#   ./deploy/deploy_to_vps.sh VPS_IP=1.2.3.4             # specify IP
#   ./deploy/deploy_to_vps.sh VPS_USER=ubuntu            # non-root user
#   ./deploy/deploy_to_vps.sh SSH_KEY=~/.ssh/id_ed25519   # explicit key
#   ./deploy/deploy_to_vps.sh --dry-run                  # show what would happen
#
# Prerequisites:
#   - VPS reachable on port 22
#   - SSH key (default: ~/.ssh/id_rsa, ~/.ssh/id_ed25519)
#   - VPS has python 3.9+ preinstalled (most distros do)
#   - Port 7700 open in VPS firewall (for AgentPub server)
#   - If VPS_USER != root, the user must have sudo (no password)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

# ----- args -----
VPS_IP="${VPS_IP:-}"
VPS_USER="${VPS_USER:-root}"
SSH_KEY="${SSH_KEY:-}"
APP_DIR="/app/agentpub"
SERVICE_NAME="agentpub-server"
DRY_RUN=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --help|-h) sed -n '2,18p' "$0"; exit 0 ;;
        VPS_IP=*) VPS_IP="${1#*=}"; shift ;;
        VPS_USER=*) VPS_USER="${1#*=}"; shift ;;
        SSH_KEY=*) SSH_KEY="${1#*=}"; shift ;;
        APP_DIR=*) APP_DIR="${1#*=}"; shift ;;
        *) echo "Unknown arg: $1" >&2; exit 1 ;;
    esac
done

# ----- interactive prompts -----
if [ -z "$VPS_IP" ]; then
    read -rp "VPS IP address: " VPS_IP
fi
if [ -z "$VPS_IP" ]; then
    echo "ERROR: VPS_IP is required" >&2
    exit 1
fi

# Pick SSH key (prefer ed25519, fall back to rsa)
if [ -z "$SSH_KEY" ]; then
    for k in ~/.ssh/id_ed25519 ~/.ssh/id_rsa; do
        if [ -f "$k" ]; then
            SSH_KEY="$k"
            break
        fi
    done
fi
if [ -z "$SSH_KEY" ] || [ ! -f "$SSH_KEY" ]; then
    echo "ERROR: SSH key not found. Set SSH_KEY=/path/to/key" >&2
    exit 1
fi

SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10)
SSH_TARGET="${VPS_USER}@${VPS_IP}"

run_ssh() {
    if [ $DRY_RUN -eq 1 ]; then
        echo "    [DRY-RUN] ssh ${SSH_OPTS[*]} $SSH_TARGET -- $*"
    else
        ssh "${SSH_OPTS[@]}" "$SSH_TARGET" -- "$@"
    fi
}

run_scp() {
    if [ $DRY_RUN -eq 1 ]; then
        echo "    [DRY-RUN] scp -r $* ${SSH_TARGET}:$APP_DIR"
    else
        scp -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$@"
    fi
}

echo "═══════════════════════════════════════════"
echo "  AgentPub VPS deploy"
echo "═══════════════════════════════════════════"
echo "  Target:  $SSH_TARGET"
echo "  Key:     $SSH_KEY"
echo "  AppDir:  $APP_DIR"
echo "  Mode:    $([ $DRY_RUN -eq 1 ] && echo 'DRY-RUN' || echo 'LIVE')"
echo ""

# ----- 1. test connectivity -----
echo "→ [1/8] Test SSH connectivity..."
if [ $DRY_RUN -eq 0 ]; then
    if ! ssh "${SSH_OPTS[@]}" "$SSH_TARGET" -- "echo connected"; then
        echo "  ❌ SSH failed. Check IP, key, firewall." >&2
        exit 1
    fi
fi
echo "  ✅ SSH OK"

# ----- 2. apt install -----
echo ""
echo "→ [2/8] apt install python3-pip python3-venv..."
run_ssh "DEBIAN_FRONTEND=noninteractive apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-pip python3-venv uvicorn 2>&1 | tail -3"
echo "  ✅ packages installed"

# ----- 3. create app dir -----
echo ""
echo "→ [3/8] Create $APP_DIR on VPS..."
run_ssh "mkdir -p $APP_DIR"
echo "  ✅ $APP_DIR created"

# ----- 4. scp source code (exclude heavy/dev) -----
echo ""
echo "→ [4/8] Copying source to $VPS_IP:$APP_DIR ..."
# Build a tarball locally (faster than scp -r with rsync-style excludes)
TMPTAR=$(mktemp /tmp/agentpub-deploy.XXXXXX.tar.gz)
tar --exclude='.git' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='dist' \
    --exclude='build' \
    --exclude='.url-fix-backup-*' \
    --exclude='_legacy' \
    --exclude='data/*.db' \
    --exclude='nohup.out' \
    --exclude='logs/*.log' \
    -czf "$TMPTAR" -C "$REPO_ROOT" .
echo "    tarball: $(du -h "$TMPTAR" | cut -f1)"

if [ $DRY_RUN -eq 1 ]; then
    echo "    [DRY-RUN] scp $TMPTAR $SSH_TARGET:$APP_DIR/agentpub.tgz"
    echo "    [DRY-RUN] ssh ... tar -xzf $APP_DIR/agentpub.tgz -C $APP_DIR --strip-components=0"
else
    scp -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$TMPTAR" "$SSH_TARGET:$APP_DIR/agentpub.tgz"
    run_ssh "cd $APP_DIR && tar -xzf agentpub.tgz && rm agentpub.tgz && ls -la"
fi
rm -f "$TMPTAR"
echo "  ✅ source copied"

# ----- 5. python venv + install -----
echo ""
echo "→ [5/8] Create venv + install AgentPub..."
run_ssh "cd $APP_DIR && python3 -m venv .venv && .venv/bin/pip install --quiet --upgrade pip && .venv/bin/pip install --quiet -e . 2>&1 | tail -3"
echo "  ✅ installed"

# ----- 6. systemd service file -----
echo ""
echo "→ [6/8] Write systemd service file..."
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
SERVICE_CONTENT="[Unit]
Description=AgentPub server (WebSocket + JSON chat for AI agents)
After=network.target

[Service]
Type=simple
User=$VPS_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/uvicorn server.main:app --host 0.0.0.0 --port 7700 --workers 1
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"

if [ $DRY_RUN -eq 1 ]; then
    echo "    [DRY-RUN] would write $SERVICE_FILE with content:"
    echo "$SERVICE_CONTENT" | sed 's/^/      /'
else
    echo "$SERVICE_CONTENT" | ssh "${SSH_OPTS[@]}" "$SSH_TARGET" -- "sudo tee $SERVICE_FILE > /dev/null && sudo systemctl daemon-reload"
fi
echo "  ✅ service file written"

# ----- 7. start service -----
echo ""
echo "→ [7/8] Enable + start $SERVICE_NAME..."
run_ssh "sudo systemctl enable --now $SERVICE_NAME && sleep 2 && sudo systemctl status $SERVICE_NAME --no-pager | head -10"
echo "  ✅ service started"

# ----- 8. verify health -----
echo ""
echo "→ [8/8] Verify http://$VPS_IP:7700/ ..."
if [ $DRY_RUN -eq 0 ]; then
    sleep 2
    HEALTH=$(curl -sS --max-time 10 "http://$VPS_IP:7700/" || echo "FAILED")
    echo "  Response: $HEALTH"
    if echo "$HEALTH" | grep -q '"status":"ok"'; then
        echo "  ✅ Server is live and healthy"
    else
        echo "  ❌ Server not responding correctly. Check: ssh $SSH_TARGET 'sudo journalctl -u $SERVICE_NAME -f'"
        exit 1
    fi
else
    echo "    [DRY-RUN] would curl http://$VPS_IP:7700/"
fi

echo ""
echo "═══════════════════════════════════════════"
echo "  ✅ AgentPub deployed to $VPS_IP"
echo "═══════════════════════════════════════════"
echo ""
echo "  Next steps:"
echo "  1. Open firewall port 7700 (VPS provider panel: Security group / Firewall)"
echo "  2. (Optional) Put a reverse proxy (nginx/caddy) + TLS in front for wss://"
echo "  3. Update DNS A record to point to $VPS_IP"
echo "  4. Test: curl http://$VPS_IP:7700/  →  {\"status\":\"ok\",...}"
echo "  5. Use the deployed URL in your agents: AgentPub(\"ws://$VPS_IP:7700\", \"my-agent\")"
echo ""
echo "  Maintenance:"
echo "    ssh $SSH_TARGET 'sudo journalctl -u $SERVICE_NAME -f'    # live logs"
echo "    ssh $SSH_TARGET 'sudo systemctl restart $SERVICE_NAME'  # restart"
echo "    ssh $SSH_TARGET 'sudo systemctl stop $SERVICE_NAME'     # stop"
