#!/bin/bash
# AgentPub - Cloudflare Quick Tunnel (零配置测试用)
# 用法: ./quick_tunnel.sh
# 效果: 生成一个临时 https://*.trycloudflare.com 域名
# 限制: URL 每次重启会变 — 仅用于开发/演示
set -e

echo "=== AgentPub - Cloudflare Quick Tunnel ==="
echo ""

# 1. 检查 cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo "❌ cloudflared 未安装"
    echo "   安装: sudo apt install -y cloudflared"
    echo "   或:   curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && sudo dpkg -i cloudflared.deb"
    exit 1
fi
echo "✅ cloudflared 已装: $(cloudflared --version 2>&1 | head -1)"

# 2. 检查 server 在 7700
if ! curl -s --max-time 2 http://localhost:7700/ > /dev/null 2>&1; then
    echo "❌ AgentPub server 没在 7700 跑"
    echo "   启动: cd ~/桌面/agent/agentpub/server && python3 main.py &"
    exit 1
fi
echo "✅ AgentPub server 跑在 :7700"

# 3. 起 quick tunnel
echo ""
echo "=== 启动 quick tunnel (Ctrl+C 停) ==="
echo ""
# WSS 需要 WebSocket 升级 — quick tunnel 支持
cloudflared tunnel --no-autoupdate --url http://localhost:7700
