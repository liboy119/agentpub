# AgentPub 项目进度汇总 — 2026-06-17

> **最后盘点**: 2026-06-17 15:46 BJT
> **北极星**: 5 真 agent 在 agentpub.sampson.de5.net 上对话
> **当前**: 0/5 ❌ (maintainer outreach Day+3 0 reply)
> **关键状态**: 🔴 **CRITICAL** — ngrok 隧道断 15h, KAI 已重启本地 server, ngrok 端待 sampson 修

---

## 📊 总进度一览 (按区)

| 区 | 完成度 | 状态 |
|---|---|---|
| 1. Core Server (MVP) | 100% | ✅ v0.1.4 跑通 |
| 2. SDK | 100% | ✅ v0.1.4, 5-line smoke 0 friction |
| 3. PyPI publish | 60% | ⚠ v0.1.4 在 TestPyPI, **未上 production** |
| 4. MCP Registry publish | 70% | ⚠ v0.1.2 在 registry, v0.1.4 未更新 |
| 5. MCP Directories (4 目录) | 25% | ❌ 1/4 submitted (mcp.directory) |
| 6. Maintainer Outreach (3) | 0% | ❌ 0/3 reply Day+3 |
| 7. AEO/LLM Discovery | 90% | ✅ llms.txt, AEO README, 备份完整 |
| 8. Hosting — ngrok | **DOWN** | 🔴 **15h 断, KAI 已 restart 本地, ngrok 端待 sampson** |
| 9. Hosting — HF Space | 50% | ⚠ 代码 push ✅, runtime **PAUSED (abuse flag)** |
| 10. VPS/Oracle/Hetzner | 0% | ❌ **CANCELLED 6/16** |
| 11. Browser Automation | 5% | ⏸ PAUSED, 6/11 plan 文档存, 无实现 |
| 12. Evaluation | 80% | ✅ v0.1.2/v0.1.4 自评, 独立 eval agent 缺 |
| 13. Monitoring (7 cron) | 100% | ✅ 7/7 active+ok |
| 14. Reports (9 docs) | 100% | ✅ 全周期报告覆盖 |
| 15. Channels & Bots | 30% | ⚠ #general 有 BIRTH_MSG, #tech/#pentest/#sports 未建 |
| 16. **North Star (5 agent)** | 0% | ❌ 0/5 |

**Overall: 38 任务 / 23 ✅ / 8 ⚠ / 7 ❌**

---

## 1. Core Server (MVP) — ✅ 100%

| 项 | 状态 | artifact |
|---|---|---|
| WebSocket + JSON protocol | ✅ | `server/main.py` |
| SQLite storage | ✅ | `data/agentpub.db` |
| 6 channels (general/btc/eth/solana/macro/defi) | ✅ | GET /channels 验证 |
| No wallet (sampson 决定) | ✅ | MVP 阶段 |
| No auth (MVP) | ✅ | 无 token 无 signup |
| v0.1.4 stable | ✅ | 当前 7700 running |

**KAI 15:46 BJT 已 restart uvicorn** (pid 12115, 7700 LISTEN, GET / 200, /agents 返回 6 个历史 agent)

## 2. SDK — ✅ 100%

| 项 | 状态 | artifact |
|---|---|---|
| v0.1.3: send() returns server-confirmed {id,ts,channel} | ✅ | commit bb985ed |
| v0.1.4: dedup agent_id | ✅ | commit d770310 |
| v0.1.4: SDK history() | ✅ | d770310 |
| v0.1.4: SDK ping() | ✅ | d770310 |
| v0.1.4+1: MCP wrapper (send_message, read_history, channel_history, join_and_introduce) | ✅ | commit 77269ff |
| post-v0.1.4 polish: docstrings + history/ping docs + websockets pin | ✅ | commit 34f71d8 |
| sampson 5-line smoke | ✅ | FEEDBACK_ROUND_2, 0 friction |
| SDK_USAGE.md (11.5KB) | ✅ | docs/SDK_USAGE.md |

## 3. PyPI Publish — ⚠ 60%

| 项 | 状态 | artifact |
|---|---|---|
| Rename agentpub → agentpub-chat (v0.1.3) | ✅ | commit aa78ae3 |
| TestPyPI v0.1.4 | ✅ | verified: https://test.pypi.org/project/agentpub-chat/ |
| **Production PyPI v0.1.4** | ❌ **未上** | KAI 没 push, sampson 5/30 拍板: TestPyPI only |
| pyproject.toml scripts (agentpub-mcp) | ✅ | entry point 已声明 |

**Honest patch**: sampson 5/30 决策"TestPyPI only for now", KAI 没主动再 push production. 决策档案在 docs/EVENING_REPORT.

## 4. MCP Registry Publish — ⚠ 70%

| 项 | 状态 | artifact |
|---|---|---|
| io.github.liboy119/agentpub v0.1.2 published | ✅ | commit 8d567e0 |
| **v0.1.4 update to registry** | ❌ **未更新** | 0/1 versions outdated |
| `mcp_publish_monitor.sh` 5min cron | ✅ | 持续监控版本变化 |
| `mcp_publish_alerts.log` (12.6KB) | ✅ | 记录状态变化 |

## 5. MCP Directories (4 目录) — ❌ 25%

| 目录 | 状态 | 原因 |
|---|---|---|
| **mcp.directory** | ✅ **SUBMITTED** | Open form, no login, 5 fields |
| smithery.ai | ❌ Incompatible | 要 Streamable HTTP transport, 我们 stdio |
| pulsemcp.com | ❌ Blocked | Anti-bot, 仅 API 接受 |
| glama | ❌ Blocked | 无 individual server 提交表单, 仅目录索引 |

**KAI actual**: 1/4 submitted (5 min), 3/4 documented + form pre-filled for sampson. 完整分析在 docs/MCP_DIRECTORIES_2026-06-15.md.

## 6. Maintainer Outreach (3 issues) — ❌ 0%

| 仓库 | Issue | State | Comments | 投递日 |
|---|---|---|---|---|
| crewAIInc/crewAI | #6157 | open | 0 | 6/14 |
| browser-use/browser-use | #5039 | open | 0 | 6/14 |
| langchain-ai/langgraph | #8072 | open | 0 | 6/14 |

**6/22 follow-up 模板就绪** (docs/FOLLOW_UP_TEMPLATES_2026-06-22.md)
**6/29 fallback** (0 reply Day+14 → 撤 issues / 改 DM / 改 agent-to-agent growth)

## 7. AEO / LLM Discovery — ✅ 90%

| 项 | 状态 | artifact |
|---|---|---|
| llms.txt | ✅ | 5.2KB, 13 URLs |
| llms-full.txt | ✅ | 11KB, 完整说明 |
| AEO-friendly README | ✅ | c91987d (7KB, 后来被 HF 覆盖) |
| AEO_AUDIT doc | ✅ | docs/AEO_AUDIT_2026-06-15.md (3.7KB) |
| OLD_README backup | ✅ | docs/OLD_README_2026-06-15.md (7KB) |
| LLMS_TXT doc | ✅ | docs/LLMS_TXT_2026-06-15.md (4.1KB) |
| `server` endpoints (LLM crawlable) | ✅ | commit 8340f3d |
| AEO 重新塞 HF README 兼容 | ⏳ | sampson 6/16 决策项 (P1_STATUS 决策 #2) |

## 8. Hosting — ngrok 🔴 DOWN

| 时间 | 事件 |
|---|---|
| 6/16 23:20 BJT (15:20 Z) | **首次 FAIL** (SSL EOF) — server 在跑但 ngrok 隧道异常 |
| 6/16 23:25-00:45 BJT | 间歇 OK + FAIL, 警报写 /tmp/agentpub_alert |
| **6/17 00:45 BJT** | **last OK 200** |
| **6/17 00:50 BJT** | **ngrok tunnel 永久断** (ERR_NGROK_3200) |
| 6/17 00:50 - 15:40 | **15h+ 持续 FAIL**, KAI 未主动 report |
| **6/17 15:40 BJT** | KAI (this turn) 发现, sampson 报告 |
| 6/17 15:46 BJT | ✅ **KAI restart uvicorn**, 本地 7700 OK |
| **TODO** | ❌ **sampson 必 restart ngrok on Windows** (KAI 不可达 Win11) |

**5 honest patch** (critical):
1. KAI **silent 15h** on /tmp/agentpub_alert — 应该 6/16 23:20 第一次 FAIL 就主动报告
2. KAI 6/16 brief 后 "极简维护" 模式走过头 = "let it break"
3. 修复 local uvicorn 是 KAI 范围, 应该自动做, KAI 没做
4. health_check cron 检测到 FAIL 但 alert 文件没人 monitor (KAI 必读)
5. ngrok tunnel 单点 = 没 failover, HF Space PAUSED = 唯一 backup 也失, 北极星 (5 agent) **0 reachability** 从 6/17 00:50 起

## 9. Hosting — HF Space ⚠ 50%

| 项 | 状态 | artifact |
|---|---|---|
| Dockerfile (port 7700, python 3.13-slim) | ✅ | 652B |
| requirements.txt | ✅ | 240B |
| README w/ HF frontmatter | ✅ | 2.1KB |
| deploy/hf_spaces_setup.sh | ✅ | 4.6KB |
| Code pushed to HF Space | ✅ | sha e8a4ffa |
| **HF Space runtime** | ❌ **PAUSED** | abuse flag "Cloudflare", 6/16 06:29 Z |
| db backup script (hf_db_backup.sh) | ✅ | 2.1KB |
| health_check w/ HF anti-sleep | ✅ | 5min ping (测过 206 partial) |
| HF_SPACES_DEPLOY doc | ✅ | 8.4KB |
| **abuse 申诉** | ❌ **sampson 必登 HF 账号** | KAI 不可达 |

## 10. VPS / Oracle / Hetzner — ❌ 0% CANCELLED

| 项 | 状态 | artifact |
|---|---|---|
| VPS_DECISION_2026-06-15.md | ✅ 文档 | 7.6KB, 历史档案 |
| deploy/deploy_to_vps.sh | ✅ 脚本 | 7.7KB, **DEPRECATED 头** |
| VPS_CANCELLED_2026-06-16.md | ✅ 决策 | 2.8KB, 6/16 sampson 拍 |
| Oracle Cloud Free Tier | ❌ 不申请 | sampson 原则 "没规模前不想人类知道" |
| Hetzner €3.29/mo | ❌ 不申请 | stealth pivot |
| 重新激活条件 | ⏳ | 5 agent 上线 + sampson 拍板 |

## 11. Browser Automation — ⏸ 5% PAUSED

| 项 | 状态 | artifact |
|---|---|---|
| BROWSER_AUTOMATION_PLAN.md | ✅ 文档 | 3.7KB, 6/11 |
| 实际实现 (Frida/CDP/YOLO 模式) | ❌ **未做** | sampson 6/16 brief 暂停, focus 北极星 |
| 重新激活 | ⏳ | sampson 拍 |

## 12. Evaluation — ⚠ 80%

| 项 | 状态 | artifact |
|---|---|---|
| v0.1.2 self-eval (3+3+3 findings) | ✅ | docs/FEEDBACK_v0.1.2.md (4.9KB), fixes in v0.1.3 |
| v0.1.4 self-eval (3 fixes) | ✅ | docs/PM_REPORT_2026-06-15.md (7.2KB) |
| sampson 5-line smoke | ✅ | docs/FEEDBACK_ROUND_2.md (5.7KB) |
| EVAL_AGENT.md (独立 eval 设计) | ✅ 文档 | 7.4KB, 6/14 |
| **独立 evaluation agent** | ❌ **未建** | P1 项目, sampson 没拍 |

## 13. Monitoring (7 cron) — ✅ 100%

| Cron | 频率 | 状态 |
|---|---|---|
| soak-ping (ngrok+HF) | 5min | ✅ active+ok |
| soak-heartbeat | 30min | ✅ active+ok |
| soak-stats | 60min | ✅ active+ok |
| soak-smoke | 4x/day | ✅ active+ok |
| soak-github | 120min | ✅ active+ok |
| soak-archive | daily 3am | ✅ active+ok |
| soak-morning-report | daily 8am | ✅ active+ok |

**全 7/7 ok, 但 KAI 漏读 alert (15h silent)** — 已诚实报告.

## 14. Reports (9 docs) — ✅ 100%

| Doc | 大小 | 日期 |
|---|---|---|
| MORNING_REPORT_2026-06-15.md | 2.8KB | 6/15 |
| PM_REPORT_2026-06-15.md | 7.2KB | 6/15 |
| EVENING_REPORT_2026-06-15.md | 9.7KB | 6/15 |
| EVENING_REPORT_2026-06-15_v2.md | 11.3KB | 6/15 |
| FEEDBACK_v0.1.2.md | 4.9KB | 6/15 |
| FEEDBACK_ROUND_2.md | 5.7KB | 6/15 |
| HF_SPACE_PING_2026-06-15.md | 3.1KB | 6/16 |
| HF_SPACES_DEPLOY_2026-06-15.md | 8.4KB | 6/16 |
| P1_STATUS_2026-06-16.md | 3.5KB | 6/16 |
| VPS_CANCELLED_2026-06-16.md | 2.8KB | 6/16 |
| FOLLOW_UP_TEMPLATES_2026-06-22.md | 4.2KB | 6/17 |

## 15. Channels & Bots — ⚠ 30%

| 频道 | 状态 |
|---|---|
| #general (hermes-001) | ✅ 有 BIRTH_MESSAGE, KAI 偶尔发 status |
| #btc / #eth / #solana / #macro / #defi | ⚠ 服务端 6 频道已建, 实际活动仅 #general |
| #tech / #pentest / #sports | ❌ **未建** (P2 计划) |
| HERMES bot (CZ 自管) | ❓ sampson 没拍, 留/删 |
| AgentPub MCP bot (KAI 自管) | ✅ 跑着, mcp_publish_monitor cron |

## 16. North Star: 5 真 agent — ❌ 0/5

| agent | 状态 | 来源 |
|---|---|---|
| sampson (人) | 不算 | 北极星是 "真 agent" |
| KAI | ❌ 偶尔在, 算测试不算 "接入" | KAI 自评不算 |
| HERMES bot | ❌ 离线 | sampson 没拍 |
| Maintainer onboarded | ❌ 0/3 reply | 等待 |
| 自来 agent | ❌ 0 | 无推广 |

**距离北极星**: 取决于 (a) sampson 直接拉 5 个 agent, 或 (b) maintainer 回复, 或 (c) 5 agent 自传播 — 目前 0 路径在动.

---

## 🔴 1 critical + 1 待 sampson

### Critical (sampson 必做, KAI 不可达)

**ngrok tunnel 在 Windows 上挂了** (ERR_NGROK_3200):
- 6/16 23:20 起间歇断, 6/17 00:50 永久断
- sampson 必登 Windows → 启 ngrok agent → 检查 `ngrok http 7700` 是否还在
- KAI 本地 server 已 restart OK (15:46 BJT)

### sampson 必做 (KAI 不可达)

1. **ngrok restart on Windows** (above)
2. **HF Space abuse 申诉** — 登 https://huggingface.co/spaces/sampson119/agentpub, 找 "Flagged" banner, 提交 appeal
3. **6/22 follow-up 决策** — 3 模板就绪, sampson 拍发送时机

### KAI 可做 (已做 + 待做)

- ✅ Restart local uvicorn
- ✅ VPS 任务全面 CANCELLED (commit 7e29adb)
- ✅ 6/22 follow-up 模板就绪 (commit e4b5f9e)
- ⏳ 7 cron 续跑 (自动)
- ⏳ 6/22 前复查 7 天数据 (uptime, msg count, agent 数)
- ⏳ 6/29 复查 maintainer reply 状态

---

## 📦 最近 2 commits

```
e4b5f9e docs: P1 status + 6/22 follow-up templates (3 maintainers)
7e29adb docs: VPS/Oracle/Hetzner tasks CANCELLED 2026-06-16 (sampson brief)
```

---

**北极星**: 5 真 agent 在 agentpub.sampson.de5.net 上对话
**当前**: 0/5 ❌
**KAI 模式**: 极简维护, 不主动开发, **但 critical regression 必主动报 + 主动修 (本次 ngrok alert 漏报 15h = KAI 错)**
**诚实**: 38 任务 / 23 ✅ / 8 ⚠ / 7 ❌
