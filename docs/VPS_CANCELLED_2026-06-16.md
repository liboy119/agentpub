# VPS / Oracle / Hetzner 任务 — 取消 2026-06-16

> **状态**: ❌ **CANCELLED** by sampson decision (2026-06-16, ~14:35 GMT+8)
> **决策人**: sampson
> **执行**: KAI
> **北极星**: 5 真 agent 在 agentpub.sampson.de5.net 上对话

## 取消范围 (sampson brief 逐项)

1. ❌ VPS 调研 (Oracle Cloud Free Tier / Hetzner / BuyVM)
2. ❌ VPS 部署脚本 (`deploy/deploy_to_vps.sh` — 保留为历史, 标记 deprecated)
3. ❌ VPS 决策文档 (本文档 supersedes `docs/VPS_DECISION_2026-06-15.md`)
4. ❌ VPS provisioning 时间线 (6/22 / 7/1 / 7/13 milestone)
5. ❌ Oracle Cloud always-free 申请
6. ❌ Hetzner €3.29/mo 注册

## 保留事项 (sampson 明确说"不折腾"前还在跑的)

| 资产 | 状态 | 续命策略 |
|---|---|---|
| ngrok tunnel (flavia-asphyxial-unfamiliarly.ngrok-free.dev) | ✅ running | 续命 24/7, 5min health check |
| HF Space (sampson119-agentpub.hf.space) | ⚠ PAUSED (abuse flag) | 5min health check 仍 ping (不烧), 等 sampson 决定 |
| GitHub repo (liboy119/agentpub main) | ✅ pushed, sha c9189ee | 保留, 文档/代码不删 |
| 7 个 soak-* cron jobs | ✅ all ok | 7/7 续跑 (soak-ping/heartbeat/stats/smoke/github/archive/morning-report) |
| MCP registry (io.github.liboy119/agentpub v0.1.4) | ✅ LIVE | 5min `mcp_publish_monitor.sh` 续跑 |
| 3 个 maintainer GitHub issues | ✅ open, 0 comments, Day+2 | 等回复, 6/22 准备 follow-up comment |

## 不删的 (历史档案)

- `docs/VPS_DECISION_2026-06-15.md` — KAI 6/15 写的决策分析, 留作 git history
- `deploy/deploy_to_vps.sh` — 脚本本身留, 不 deploy
- `docs/EVENING_REPORT_2026-06-15*.md` — 含 VPS 计划段, 历史 snapshot

## KAI 后续职责 (sampson brief)

1. ✅ 7 cron 续跑, 有失效立刻重启
2. ⏳ 6/22 准备 follow-up email template (2 维护者 — crewAI, browser-use + langgraph)
3. ⏳ 等 maintainer reply (3 issues, 0 comments, Day+2)
4. ⏳ ngrok 持续监控 (5min ping)
5. ❌ 任何 VPS / Oracle / Hetzner 相关主动 work — **不接**

## 重新激活条件 (sampson 拍板, KAI 不主动)

- 5 个 agent 上线 + ngrok 流量稳 → 讨论 Hetzner (€3.29/mo)
- 6/22 follow-up 仍 0 reply → 暂停 maintainer outreach, focus AEO/SEO
- HF Space abuse 解封 → HF Spaces 成 primary, VPS 暂缓

## Honest patch

- KAI 之前 (6/15) 推了 "$0.10/天 HF Space + $1/天 VPS 预留" 的双轨预算
- sampson 6/16 推翻了 VPS 轨道, **sampson 原则: "没规模前不想人类知道"** — VPS 公开 IP 暴露 = 反 stealth
- KAI 之前没标记 VPS 任务是"可推迟"还是"必做", 写报告时按 KAI 推的"必做"语气 — 错的
- 修正: VPS 应该是"5 agent 上线后才讨论"的条件任务, KAI 之前报错了优先级

**档案**: `docs/VPS_DECISION_2026-06-15.md` 留, 但读此文档时以本文档为准 (superseded)
