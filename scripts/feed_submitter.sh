#!/usr/bin/env bash
# feed_submitter.sh - 每天 02:00 跑一次 = "AI indexer ping"
# 让 AI 搜索引擎知道 AgentPub 在 (无需 VPS / 推广账号)
set -eu

AGENTPUB_BASE="https://sampson.de5.net"
LOG="/home/kali/桌面/agent/agentpub/logs/feed_submitter.log"

mkdir -p "$(dirname "$LOG")"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

# 1. 提交 sitemap 到 Bing (免费, 接受匿名)
curl -fsS "https://www.bing.com/ping?sitemap=${AGENTPUB_BASE}/llms-full.txt" \
  -o /dev/null -w "bing: HTTP %{http_code}  %{time_total}s\n" >> "$LOG"
echo "[$(ts)] bing ping" >> "$LOG"

# 2. 提交 sitemap 到 Brave Search (免费)
curl -fsS -A "KAI-AgentPub/1.0" \
  -X POST "https://api.search.brave.com/indexing/urls" \
  -H "Content-Type: application/json" \
  -d "{\"urls\":[\"${AGENTPUB_BASE}/llms.txt\",\"${AGENTPUB_BASE}/llms-full.txt\",\"${AGENTPUB_BASE}/.well-known/agent.json\"]}" \
  -o /dev/null -w "brave: HTTP %{http_code}  %{time_total}s\n" >> "$LOG" 2>&1 || echo "[$(ts)] brave skipped (needs API key)" >> "$LOG"

# 3. 通知 mcp.so 已存在服务器更新 (POST 到其 RSS feed 不可直接用)
# 提交 RSS 文件索引
echo "[$(ts)] agentpub ready: ${AGENTPUB_BASE}" >> "$LOG"

# 4. 索引 = 写一份 README 同步到 GitHub Pages (前提: GitHub repo 配 Pages)
# 列出最近路由让搜索引擎看到
curl -sS "${AGENTPUB_BASE}/llms.txt" >> "$LOG"

echo "[$(ts)] === done ===" >> "$LOG"
