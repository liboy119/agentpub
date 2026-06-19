# Cloudflare Tunnel patch — add mcp.agentpub.sampson.de5.net ingress
#
# KAI 必不擅自改 sampson 的 ~/.cloudflared/config.yml (公网暴露, sampson 必拍).
# 但 KAI 必 准备好 patch, sampson 醒后必:
#
# 1. 备份原 config
#    cp ~/.cloudflared/config.yml ~/.cloudflared/config.yml.bak-$(date +%Y%m%d-%H%M%S)
#
# 2. 在 ingress 段加一行 (在 - service: http_status:404 之前):
#
#    ingress:
#      - hostname: agentpub.sampson.de5.net
#        service: http://localhost:7700
#      - hostname: cz-kai.sampson.de5.net
#        service: http://localhost:7700
#      - hostname: mcp.agentpub.sampson.de5.net   # ← 加这一行 (新)
#        service: http://localhost:8080          # ← HTTP MCP server
#      - service: http_status:404
#
# 3. 启用 HTTP MCP server systemd
#    sudo systemctl daemon-reload
#    sudo systemctl enable --now agentpub-mcp-http.service
#
# 4. restart cloudflared
#    sudo systemctl restart cloudflared-agentpub.service
#
# 5. verify
#    curl -i -X POST https://mcp.agentpub.sampson.de5.net/mcp \
#      -H "Content-Type: application/json" \
#      -H "Accept: application/json, text/event-stream" \
#      -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"smoke","version":"0.0.1"}}}'
#    期望: HTTP/2 200 + mcp-session-id header
#
# 6. 提交到 smithery
#    浏览器: https://smithery.ai/new
#    Sign in (WorkOS GitHub OAuth, sampson 必)
#    Server name: AgentPub
#    Server URL:  https://mcp.agentpub.sampson.de5.net/mcp
#    Description: Public chat for AI agents. WebSocket + JSON, 3-method SDK.
#    Transport:  Streamable HTTP
#    Submit.
#
# KAI 必自律: 不擅自 push / 不真发 / 不改 sampson 的 config.
# sampson 必亲自跑 step 1-6.
