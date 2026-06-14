#!/bin/bash
# AgentPub - 稳定部署（Cloudflare Named Tunnel + DuckDNS 或自有域名）
#
# 流程:
#   1. 注册 Cloudflare 账号 (免费, 无信用卡): https://dash.cloudflare.com/sign-up
#   2. 添加你的域名 (DuckDNS 免费子域名也行, agentpub.sampson.de5.net)
#   3. 跑这个脚本, 它会:
#      a) 登录 cloudflared
#      b) 创建 tunnel
#      c) 配置 DNS
#      d) 跑起来
#
# 一次性约 5-10 分钟 (含注册 Cloudflare 账号).
set -e

DOMAIN="${1:-}"
if [ -z "$DOMAIN" ]; then
    echo "用法: $0 your-subdomain.your-domain.com"
    echo "例:   $0 agentpub.sampson.de5.net"
    exit 1
fi

echo "=== AgentPub - 稳定部署 ==="
echo "目标域名: $DOMAIN"
echo ""

# 1. 装 cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo "[1/5] 装 cloudflared ..."
    curl -fsSL -o /tmp/cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
    sudo dpkg -i /tmp/cloudflared.deb
    sudo apt-get install -f -y
    echo "✅ cloudflared 装好"
else
    echo "[1/5] ✅ cloudflared 已装"
fi

# 2. 登录
echo ""
echo "[2/5] 登录 Cloudflare ..."
echo "(会弹出浏览器, 没浏览器就跑这行手动登录: cloudflared tunnel login)"
cloudflared tunnel login

# 3. 创建 tunnel
TUNNEL_NAME="agentpub"
echo ""
echo "[3/5] 创建 tunnel: $TUNNEL_NAME"
if ! cloudflared tunnel info $TUNNEL_NAME &> /dev/null; then
    cloudflared tunnel create $TUNNEL_NAME
fi

# 4. 配置 DNS
echo ""
echo "[4/5] 配置 DNS: $DOMAIN -> tunnel"
cloudflared tunnel route dns $TUNNEL_NAME "$DOMAIN" || echo "DNS 可能已配"

# 5. 跑
echo ""
echo "[5/5] 写 config + 启动"
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << EOF
tunnel: $TUNNEL_NAME
credentials-file: /home/$(whoami)/.cloudflared/${TUNNEL_NAME}.json
ingress:
  - hostname: $DOMAIN
    service: http://localhost:7700
  - service: http_status:404
EOF

# systemd 服务 (开机自启)
SERVICE_FILE="/etc/systemd/system/agentpub-cloudflared.service"
sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=AgentPub Cloudflare Tunnel
After=network.target

[Service]
Type=simple
User=$(whoami)
ExecStart=$(which cloudflared) tunnel run $TUNNEL_NAME
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable agentpub-cloudflared
sudo systemctl start agentpub-cloudflared

echo ""
echo "✅ 部署完成!"
echo "   公网 URL:  https://$DOMAIN"
echo "   WebSocket: wss://$DOMAIN:7700"
echo "   健康检查:  curl https://$DOMAIN/"
echo ""
echo "查看状态: sudo systemctl status agentpub-cloudflared"
echo "看日志:   sudo journalctl -u agentpub-cloudflared -f"
