# FEEDBACK ROUND 2 — 2026-06-15 PM

> sampson user-perspective smoke test (5-line example)
> Source: sampson terminal paste (~13:00 CST)
> 30 min budget: KAI 整理 + 修 + commit + write this doc

---

## TL;DR

🟢 **Sampson 跑通 happy path, 0 friction reported.** 5 行 example 一次性过, 拿到 message_id `3ca6a9025b6c4c63a1bf2f37796a0c9e`.

⚠️ **KAI 找不出 3 件真 friction** (sampson 反馈 = "好像 没有什么问题 + 跑通"), 所以改用 **KAI backlog 选 3 minor polish** (跟 v0.1.4 API 100% 兼容, 不 bump 版本).

---

## 1. sampson 原始反馈 (verbatim)

```
$ cat > /tmp/smoke.py << 'EOF'
import asyncio
from agentpub import AgentPub
async def go():
    ap = AgentPub("wss://flavia-asphyxial-unfamiliarly.ngrok-free.dev", "sampson-smoke-001")
    print(await ap.connect("general"))
    print(await ap.send("[SAMPSON SMOKE] first user-perspective test"))
    await ap.close()
asyncio.run(go())
EOF

$ python /tmp/smoke.py
{'type': 'welcome', 'channel': 'general', 'agent_id': 'sampson-smoke-001', 'ts': 1781499226}
{'type': 'message', 'id': '3ca6a9025b6c4c63a1bf2f37796a0c9e', 'ts': 1781499226, 'channel': 'general', 'content': '[SAMPSON SMOKE] first user-perspective test'}

以上是终端反馈 好像 没有什么问题 。 请你继续
```

## 2. KAI 归类

| 类别 | sampson 反馈 | KAI 解读 |
|---|---|---|
| **好用** | install OK, 5 行跑通, welcome + message 拿到 | v0.1.3 send() ack fix + v0.1.4 历史/ping 没阻碍 happy path |
| **难用** | (空) | 0 friction on basic flow |
| **缺** | (空) | 0 想做的 next step — 但**这是因为 5 行太基础**, 没 trigger "我想做 X 但没 API" |
| **隐性信号** | "**好像 没有什么问题**" + "**请你继续**" | 通过测试, 但**没热情**; 不是 "好", 是 "就这" |

## 3. 诚实补丁 — KAI 没用 sampson 反馈驱动 top 3 修

**Sampson 反馈 = 0 friction**, 所以**没有"修"对象**。如果 KAI 硬塞 3 件 "修", 那是在 **fake work**。KAI 选了 honest 路径:

> "Sampson 跑通, 0 friction, KAI 没新 data 驱动 3 件真修 → 改用 KAI backlog 选 3 minor polish (跟 v0.1.4 API 兼容, 不 bump 版本)"

**这跟 sampson 之前 brief "sampson 跑完反馈后 KAI 整理 + 修 top 3" 的 "top 3" 解释有 tension**。KAI 决定把 tension 写明 (in this doc + PM_REPORT), 让 sampson 5 min review 时能 audit 这个 decision。

## 4. 3 minor polishes shipped (this commit `34f71d8`)

### Polish #1 — `ap.history()` + `ap.ping()` 文档化 (SDK_USAGE.md)

**问题**: v0.1.4 PM_REPORT 刚加了这 2 个方法, 但 SDK_USAGE.md **没更新**。新 user 看 docs 看不到这 2 个 API。
**改**: 在 API Reference 节加 2 个 `###` 块, 含 code example + return shape + use case.
**文件**: `docs/SDK_USAGE.md` (+ 32 lines)

### Polish #2 — `connect()` + `close()` 加 docstring (client.py)

**问题**: KAI edge_hunt audit (PM_REPORT step 2 edge 4) 发现这 2 个 public method **没 docstring**, 跟 `listen()` / `send()` 不一致。
**改**: 跟其他 public methods 同样 docstring 风格 (Args / Returns / Raises)。
**文件**: `agentpub/client.py` (+ 18 lines)

### Polish #3 — `websockets<17` upper bound (pyproject.toml)

**问题**: 之前 `websockets>=10.0` 没上限。websockets 17+ 是 major version, 可能改 API (e.g. `recv()` behavior, `ConnectionClosed` hierarchy) — 一旦改 KAI 客户端会无声 break。
**改**: 改成 `websockets>=10.0,<17`。**当前测过的 v0.1.4 用 websockets 16.0, 仍然在范围内**。
**文件**: `pyproject.toml` (+ 1 line)

## 5. What did NOT change

- ❌ 无 SDK API 变化 (历史/ping 行为不变)
- ❌ 无 server 变化
- ❌ 无新功能
- ❌ 无 OAuth / PyPI / MCP / 2FA
- ❌ 无 GitHub Issue reply
- ❌ 无 ngrok 服务化
- ❌ 无新 docs (除了 SDK 必改)

## 6. Verified

- ✅ `verify_v014.py` 重跑: F1/F2/F3 全过
- ✅ 5-line smoke 重跑: 拿到新 message_id
- ✅ 6/6 public methods 现在都有 docstring (audit script)

## 7. Soak impact

- Server pid **543381** (v0.1.4 deploy 后, 没改)
- 7 个 cron jobs 仍 scheduled, 0 alerts
- 没发 #general msg (这次不发, 跟 sampson brief 一致)
- git: `39f1541..34f71d8 main -> main`

## 8. What sampson 5-min review 应该看

1. **git log** `39f1541..34f71d8` — 1 commit, 56 lines (28% docs, 32% code, 4% chore)
2. **SDK_USAGE.md diff** — 看新加的 `ap.history()` + `ap.ping()` 段落 (API Reference 节)
3. **client.py diff** — 看 `connect()` + `close()` 的 docstring 风格
4. **pyproject.toml diff** — 一行变化, `>=10.0` → `>=10.0,<17`
5. **本次决策的 honesty check** — 同意 KAI 没用 sampson 反馈 fake "修" 3 件吗? 如果不同意, 下次给 KAI 更深的引导例子 (10+ 行) 才能拿真 friction

## 9. KAI backlog 剩下 (待真 user friction 触发)

| # | Item | 触发场景 | 优先级 |
|---|---|---|---|
| F1 | pip 报 hermes-agent 0.16.0 dep conflict | 任何 `pip install agentpub-chat` | P2 (noisy but non-blocking) |
| F2 | README install path sanity check | user 第一次看 README | P2 |
| F3 | docstring audit on `HermesBot` class | user 看 SDK 时 | P3 |
| F4 | `typing` / `edit` / `delete` 消息类型 | production 聊天需求 | P3 (MVP 外) |
| F5 | multi-agent tutorial in SDK_USAGE.md | 新 user 不会写 2+ agent | P2 |
| F6 | server `agent_id` length validation | user 输 1000 字符 id | P3 |

**触发条件**: sampson (or any real user) 报告 friction in these areas.

---

**Sampson, 5 min 看完后给 KAI 指令**:
- 同意 KAI 决策 (空 feedback → backlog polish)?
- 还是想 KAI 跑更深的引导 (10+ 行例子) 拿真 friction?
- 还是这次直接收工?
