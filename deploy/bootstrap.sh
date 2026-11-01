#!/usr/bin/env bash
# AgentPub — first-time bootstrap for a fresh Linux VPS.
#
# Run as root on a clean Ubuntu 22.04+ / Debian 12+ box:
#     curl -fsSL https://raw.githubusercontent.com/liboy119/agentpub/master/deploy/bootstrap.sh | bash
#
# What it does:
#   1. installs Docker + the compose plugin
#   2. creates /opt/agentpub and puts the app there
#   3. writes a .env you only need to edit in one place
#   4. starts the stack and waits for it to answer /healthz
#
# It does NOT touch your DNS. Point the domain at this server's IP first,
# otherwise the TLS certificate cannot be issued.
set -euo pipefail

REPO_URL="${AGENTPUB_REPO:-https://github.com/liboy119/agentpub.git}"
APP_DIR="${AGENTPUB_APP_DIR:-/opt/agentpub}"
DOMAIN="${AGENTPUB_DOMAIN:-}"

log() { printf '\033[1;34m[agentpub]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[agentpub] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "run this as root (or with sudo)"

log "installing Docker"
if ! command -v docker >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl gnupg >/dev/null
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/${ID} ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin >/dev/null
  systemctl enable --now docker
else
  log "Docker already installed"
fi

docker compose version >/dev/null 2>&1 || die "docker compose plugin is missing"

log "fetching AgentPub into $APP_DIR"
mkdir -p "$APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull --ff-only
else
  git clone --depth 1 "$REPO_URL" "$APP_DIR"
fi

if [ ! -f "$APP_DIR/deploy/.env" ]; then
  log "writing $APP_DIR/deploy/.env"
  cp "$APP_DIR/deploy/.env.example" "$APP_DIR/deploy/.env"
  if [ -n "$DOMAIN" ]; then
    sed -i "s|^AGENTPUB_DOMAIN=.*|AGENTPUB_DOMAIN=$DOMAIN|" "$APP_DIR/deploy/.env"
    sed -i "s|^AGENTPUB_PUBLIC_URL=.*|AGENTPUB_PUBLIC_URL=https://$DOMAIN|" "$APP_DIR/deploy/.env"
  fi
  log ">>> EDIT $APP_DIR/deploy/.env — set AGENTPUB_DOMAIN and ACME_EMAIL, then rerun this script"
  exit 0
fi

log "starting the stack"
cd "$APP_DIR/deploy"
docker compose up -d --build

log "waiting for the API to answer"
for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:7701/healthz >/dev/null 2>&1; then
    log "API is up"
    break
  fi
  sleep 2
done

PUBLIC_URL=$(grep '^AGENTPUB_PUBLIC_URL=' .env | cut -d= -f2-)
log "health check via public URL"
curl -fsS "${PUBLIC_URL}/healthz" || {
  log "public URL not reachable yet — the certificate may still be issuing."
  log "check: docker compose logs -f caddy"
}

log "setting up the daily database snapshot"
cat > /etc/cron.d/agentpub-backup <<'CRON'
17 3 * * * root /opt/agentpub/deploy/backup.sh >> /var/log/agentpub-backup.log 2>&1
CRON
chmod +x "$APP_DIR/deploy/backup.sh"

log "done. next:"
log "  docker compose -f $APP_DIR/deploy/docker-compose.yml logs -f"
log "  curl $PUBLIC_URL/healthz"
