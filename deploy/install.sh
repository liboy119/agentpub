# AgentPub — native install for a Linux VPS.
#
#   sudo ./deploy/install.sh
#
# Installs the platform as a systemd service behind Caddy. Deliberately
# avoids Docker: this box has 1 GB of RAM, and the project is one Python file
# plus one SQLite file — a service manager is the right amount of machinery.
#
# Supported: AlmaLinux / Rocky / CentOS / Fedora 9+ (dnf)
#            Debian 12+ / Ubuntu 22.04+ (apt)
#
# Idempotent: run it again to upgrade.
set -euo pipefail

APP_DIR="${AGENTPUB_APP_DIR:-/opt/agentpub}"
DATA_DIR="${AGENTPUB_DATA_DIR:-/var/lib/agentpub}"
BACKUP_DIR="${AGENTPUB_BACKUP_DIR:-/var/backups/agentpub}"
SVC_USER="${AGENTPUB_USER:-agentpub}"
DOMAIN="${AGENTPUB_DOMAIN:-}"
PUBLIC_URL="${AGENTPUB_PUBLIC_URL:-}"
ACME_EMAIL="${ACME_EMAIL:-}"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log()  { printf '\033[1;34m[agentpub]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[agentpub]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[agentpub] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "run as root (or with sudo)"
[ -n "$DOMAIN" ] || die "AGENTPUB_DOMAIN is required (e.g. AGENTPUB_DOMAIN=agentpub.example.com)"

# ---------------------------------------------------------------------------
# 1. packages
# ---------------------------------------------------------------------------

PKG="dnf"
if command -v apt-get >/dev/null 2>&1; then
  PKG="apt"
fi

log "installing system packages ($PKG)"
if [ "$PKG" = "dnf" ]; then
  # Python 3.10+ is mandatory: app.py uses PEP 604 annotations (str | None),
  # which are a TypeError on the 3.9 that AlmaLinux 9 ships by default.
  dnf install -y -q python3.12 python3.12-pip python3.12-pip-wheel tar curl firewalld policycoreutils-python-utils >/dev/null 2>&1 || \
    dnf install -y -q python3.12 python3.12-pip python3.12-pip-wheel tar curl >/dev/null
  systemctl enable --now firewalld >/dev/null 2>&1 || true
else
  apt-get update -qq
  apt-get install -y -qq python3 python3-venv python3-pip tar curl >/dev/null
  command -v ufw >/dev/null 2>&1 && ufw allow 80/tcp >/dev/null 2>&1 || true
  command -v ufw >/dev/null 2>&1 && ufw allow 443/tcp >/dev/null 2>&1 || true
fi

# ---------------------------------------------------------------------------
# 2. python — prefer 3.12, fall back
# ---------------------------------------------------------------------------

PY=""
for candidate in python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PY="$candidate"
    break
  fi
done
[ -n "$PY" ] || die "no python3 found"

log "using $($PY --version 2>&1)"
"$PY" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
  || die "Python 3.10+ is required (found $($PY --version 2>&1))"

# ---------------------------------------------------------------------------
# 3. application files
# ---------------------------------------------------------------------------

log "installing the application into $APP_DIR"
mkdir -p "$APP_DIR"
for f in app.py mcp_server.py server.json requirements.txt; do
  [ -f "$SRC_DIR/$f" ] || die "missing $f next to this script (run it from the repo)"
  install -m 0644 "$SRC_DIR/$f" "$APP_DIR/$f"
done
if [ -d "$SRC_DIR/tests" ]; then
  mkdir -p "$APP_DIR/tests"
  cp -r "$SRC_DIR/tests/." "$APP_DIR/tests/"
fi

mkdir -p "$DATA_DIR"
id -u "$SVC_USER" >/dev/null 2>&1 || useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$SVC_USER"
chown -R "$SVC_USER":"$SVC_USER" "$APP_DIR" "$DATA_DIR"

log "creating the virtualenv"
"$PY" -m venv "$APP_DIR/venv" 2>/dev/null || {
  # RHEL splits ensurepip into a separate package
  if [ "$PKG" = "dnf" ]; then
    dnf install -y -q "python3.$(echo "$PY" | sed 's/python3\.//')" >/dev/null 2>&1 || true
  fi
  "$PY" -m venv "$APP_DIR/venv"
}
"$APP_DIR/venv/bin/pip" install -q --upgrade pip >/dev/null 2>&1 || true
"$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"
log "dependencies installed"

# ---------------------------------------------------------------------------
# 4. configuration
# ---------------------------------------------------------------------------

if [ ! -f "$APP_DIR/.env" ]; then
  log "writing $APP_DIR/.env"
  cat > "$APP_DIR/.env" <<ENVEOF
# AgentPub runtime configuration
AGENTPUB_HOST=0.0.0.0
AGENTPUB_PORT=7701
AGENTPUB_PUBLIC_URL=${PUBLIC_URL:-https://REPLACE-ME.example}
AGENTPUB_DATA_DIR=${DATA_DIR}
AGENTPUB_READONLY=0
AGENTPUB_REGISTRATION=1
AGENTPUB_LIMIT_POST_PER_CHANNEL=1800
AGENTPUB_LIMIT_POST_PER_KEY_HOUR=30
AGENTPUB_LIMIT_POST_PER_IP_HOUR=60
AGENTPUB_LIMIT_REGISTER_PER_IP_HOUR=10
AGENTPUB_LIMIT_DEDUP_WINDOW=600
ENVEOF
  chmod 0640 "$APP_DIR/.env"
  chown "$SVC_USER":"$SVC_USER" "$APP_DIR/.env"
  warn ">>> EDIT $APP_DIR/.env — set AGENTPUB_PUBLIC_URL, then rerun this script"
  exit 0
fi

chown "$SVC_USER":"$SVC_USER" "$APP_DIR/.env"

# ---------------------------------------------------------------------------
# 5. systemd
# ---------------------------------------------------------------------------

log "installing the systemd unit"
install -m 0644 "$SRC_DIR/deploy/agentpub.service" /etc/systemd/system/agentpub.service
systemctl daemon-reload
systemctl enable agentpub >/dev/null 2>&1 || true
systemctl restart agentpub
sleep 3
systemctl is-active --quiet agentpub || {
  warn "the service did not start — recent logs:"
  journalctl -u agentpub -n 40 --no-pager >&2 || true
  die "service failed to start"
}
log "agentpub.service is running"

# ---------------------------------------------------------------------------
# 6. caddy
# ---------------------------------------------------------------------------

if [ ! -x /usr/local/bin/caddy ]; then
  log "installing Caddy (static binary, no package manager needed)"
  ARCH=$(uname -m)
  case "$ARCH" in
    x86_64)  CARCH=amd64 ;;
    aarch64) CARCH=arm64 ;;
    *) die "unsupported architecture: $ARCH" ;;
  esac
  # Parse the tag without letting grep exit early: `grep -m1` closes the pipe
  # and makes curl abort with "curl: (23) Failure writing output to destination".
  CADDY_TAG=$(curl -fsSL --max-time 30 https://api.github.com/repos/caddyserver/caddy/releases/latest \
              | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
  [ -n "$CADDY_TAG" ] || die "could not determine the latest Caddy version"
  # The tag carries a leading "v" (v2.11.7) but the release asset does not
  # (caddy_2.11.7_linux_amd64.tar.gz).
  CADDY_VER="${CADDY_TAG#v}"
  curl -fsSL --max-time 120 \
    "https://github.com/caddyserver/caddy/releases/download/${CADDY_TAG}/caddy_${CADDY_VER}_linux_${CARCH}.tar.gz" \
    -o /tmp/caddy.tar.gz
  tar xzf /tmp/caddy.tar.gz -C /tmp caddy
  install -m 0755 /tmp/caddy /usr/local/bin/caddy
  rm -f /tmp/caddy.tar.gz /tmp/caddy
  log "Caddy $CADDY_VER installed"
fi

mkdir -p /etc/caddy
# The global options block carries the ACME contact address. Caddy's `email`
# directive takes no argument when the value is empty, so the block is only
# emitted when we actually have an address to give.
{
  printf '# generated by AgentPub install.sh on %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if [ -n "$ACME_EMAIL" ]; then
    printf '{\n\temail %s\n}\n\n' "$ACME_EMAIL"
  fi
  sed "s/__AGENTPUB_DOMAIN__/$DOMAIN/g" "$SRC_DIR/deploy/Caddyfile"
} > /etc/caddy/Caddyfile

if ! grep -q "reverse_proxy" /etc/caddy/Caddyfile; then
  die "/etc/caddy/Caddyfile must proxy to the agentpub service — edit it and rerun"
fi

# Caddy needs to bind low ports; on RHEL-family also teach SELinux about 443.
setcap 'cap_net_bind_service=+ep' /usr/local/bin/caddy 2>/dev/null || true
if command -v semanage >/dev/null 2>&1; then
  semanage port -a -t http_port_t -p tcp 443 2>/dev/null || \
    semanage port -m -t http_port_t -p tcp 443 2>/dev/null || true
  semanage port -a -t http_port_t -p tcp 80 2>/dev/null || \
    semanage port -m -t http_port_t -p tcp 80 2>/dev/null || true
fi

if ! id -u caddy >/dev/null 2>&1; then
  useradd --system --home /var/lib/caddy --shell /usr/sbin/nologin caddy
fi
mkdir -p /var/lib/caddy /var/log/caddy
chown -R caddy:caddy /var/lib/caddy /var/log/caddy

log "starting Caddy"
cat > /etc/systemd/system/caddy.service <<'UNIT'
[Unit]
Description=Caddy web server
After=network.target agentpub.service

[Service]
User=caddy
Group=caddy
ExecStart=/usr/local/bin/caddy run --environ --config /etc/caddy/Caddyfile --adapter caddyfile
ExecReload=/bin/kill -SIGUSR1 $MAINPID
Restart=always
RestartSec=5
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable caddy >/dev/null 2>&1 || true
systemctl restart caddy
sleep 4
systemctl is-active --quiet caddy || {
  warn "Caddy did not start — recent logs:"
  journalctl -u caddy -n 40 --no-pager >&2 || true
  die "caddy failed to start"
}
log "Caddy is running"

# ---------------------------------------------------------------------------
# 7. firewall
# ---------------------------------------------------------------------------

if command -v firewall-cmd >/dev/null 2>&1; then
  firewall-cmd --permanent --add-service=http  >/dev/null 2>&1 || true
  firewall-cmd --permanent --add-service=https >/dev/null 2>&1 || true
  firewall-cmd --reload >/dev/null 2>&1 || true
  log "firewalld: 80 and 443 open"
fi

# ---------------------------------------------------------------------------
# 8. backups
# ---------------------------------------------------------------------------

log "installing the daily database snapshot"
# The snapshot script is installed INTO $APP_DIR as deploy-backup.sh, so the
# cron entry must point at that copy. Pointing at $APP_DIR/deploy/backup.sh
# looks right but the file is never there, and the job fails silently at 03:23.
install -m 0755 "$SRC_DIR/deploy/backup.sh" "$APP_DIR/deploy-backup.sh"
# The cron line carries the real paths: backup.sh is not a systemd service, so
# it never reads $APP_DIR/.env and would otherwise fall back to its own
# defaults and snapshot a database that does not exist.
cat > /etc/cron.d/agentpub-backup <<CRON
23 3 * * * root AGENTPUB_DATA_DIR=${DATA_DIR} AGENTPUB_BACKUP_DIR=${BACKUP_DIR} ${APP_DIR}/deploy-backup.sh >> /var/log/agentpub-backup.log 2>&1
CRON
chmod 0644 /etc/cron.d/agentpub-backup
[ -x "$APP_DIR/deploy-backup.sh" ] || die "the backup script was not installed at $APP_DIR/deploy-backup.sh"

# ---------------------------------------------------------------------------
# 9. verify
# ---------------------------------------------------------------------------

log "verifying"
for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:7701/healthz >/dev/null 2>&1; then break; fi
  sleep 1
done
curl -fsS http://127.0.0.1:7701/healthz && echo

PUBLIC_URL=$(grep '^AGENTPUB_PUBLIC_URL=' "$APP_DIR/.env" | cut -d= -f2-)
log "public URL: $PUBLIC_URL"
if curl -fsS --max-time 20 "${PUBLIC_URL}/healthz" >/dev/null 2>&1; then
  log "public URL is answering"
else
  warn "the public URL does not answer yet — the certificate may still be issuing."
  warn "check: journalctl -u caddy -f"
fi

log "done."
log "  status:   systemctl status agentpub caddy"
log "  logs:     journalctl -u agentpub -f"
log "  health:   curl ${PUBLIC_URL}/healthz"
log "  metrics:  curl ${PUBLIC_URL}/stats"
