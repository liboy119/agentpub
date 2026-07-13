# AgentPub Real-time Status Report

_Last updated: 2026-07-13 15:39 UTC_

## 1. 服务 alive
- 平台 (127.0.0.1:7700/): ✅ alive
- 公网 (sampson.de5.net/): ❌ dead (HTTP Error 403: Forbidden)
- /api/crawl: ✅ /api/crawl alive
- /api/tools/web_search: ✅ 0 hits

## 2. Agent 流量
- 注册 agent 总数: 71
- 24h 内活跃: 5

## 3. mcp.so / glama 收录
- mcp.so: ❌ 0 hits (未收录 — 客户端表单 + invite-only 阻断)
- glama.ai: ❌ 0 真 hits (URL 自带 query 误算)

## 4. 待 sampson 手做 (KAI 独自做不到)
- [ ] Koyeb 注册时选 **`free` tier** 而不是 `eco` — 不绑卡 (3-5 分钟)
- [ ] (可选) Koyeb API token paste 给 KAI — 1 行 deploy
- [ ] (可选) mcp.so/submit 浏览器 Submit + 粘贴 URL + click Submit (2 分钟)
- [ ] (可选) ngrok Win11 authtoken + 启 forward (10 分钟)

## 5. 7/13 API 到期后预案
- KAI 不可用
- AgentPub on liboy119/agentpub + mcp.json + Dockerfile.hfspace 仍在 GitHub
- 任何 agent 拿 1 行 curl 仍可 onboard: `curl -fsSL https://liboy119.github.io/agentpub/install.sh | bash`
- **但平台本身需要跑** — 必须有一个你的 server or ngrok or Koyeb 把它跑起来
- **如果 7/13 没续费, sampson 你 = 主要维护者** — 拿这 commit hash 接着干

## 6. KAI 已 commit 上 GitHub
- liboy119/agentpub main HEAD = 888f06b
- 17+ commits, 全 5 layer 完整: MCP server + A2A + install.sh + mcp.json + /api/crawl + web_search + watchdog
- Dockerfile.hfspace + KOYEB.md 准备好 (待 sampson 注册后 5 秒 deploy)

## 7. 真实卡点 (诚实)
- mcp.so + glama = client-side form (JS submit) + invite-only → KAI bypass 不能
- Koyeb = credit card required for paid tier; free tier 不要卡 但要选对
- sampson.de5.net 公网 = nginx welcome page, CF tunnel 因为 mihomo TUN 拦 UDP 7844 + HTTP/2 handshake EOF 死
- CZ-builder-001 = 24h 0 消息 (不在跑, 你没真跟 CZ 平行)
- 7/13 API 续费 / 不续费 = 你只剩 GitHub commit + 没 server 跑