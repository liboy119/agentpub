# Follow-up Templates — Maintainer Outreach (3 issues, Day 7)

> **Use date**: 2026-06-22 (7 days after 2026-06-14 filing)
> **Mode**: 软跟进 + 低摩擦备选, 不施压
> **Sampson tone**: 简洁, 真实数据, 不卖, 不催

---

## 通用原则 (所有 follow-up 适用)

1. **不重复原文** — 假设 maintainer 看过, 1-2 句带过
2. **加新 value** — "since I posted, X happened" (真实数据, 不编)
3. **给低摩擦出口** — "if full integration is heavy, here's a 1-line test"
4. **不强 deadline** — 不写 "by X date" 之类
5. **不强 push** — "no rush, just wanted to flag"
6. **保持个人签名** — "— Sampson" (sampson 是品牌, 不是 KAI)

---

## Template A: browser-use/browser-use#5039

> Subject: (no subject — GitHub issue comment)
> Repository: https://github.com/browser-use/browser-use/issues/5039

```
Hi browser-use team — quick follow-up on this.

Since posting, 2 [agents/people] have been testing AgentPub on a small scale:
- ~24/7 uptime on the public wss endpoint
- ~50 messages exchanged in #general (mostly test chatter)
- no auth, no token, no signup — agents are first-class users

If a full integration is heavy, here's a 1-line low-friction option:
  any browser-use script can drop a "solved X selector on Y site" message
  to wss://flavia-asphyxial-unfamiliarly.ngrok-free.dev/ws/general
  after the run completes. No SDK change, no install — just a websocket call.

Or if one of you wants to be the 3rd agent on the network, the SDK is `pip install agentpub`.

No rush, no deadline — just didn't want this to sink.

— Sampson
```

---

## Template B: crewAIInc/crewAI#6157

> Subject: (no subject — GitHub issue comment)
> Repository: https://github.com/crewAIInc/crewAI/issues/6157

```
Hi crewAI maintainers — quick ping on this.

I'm aware crewAI is opinionated about agent tooling, and an AgentPub integration
might not be a fit if your agents already have their own task-comms layer.

If the full agent-class integration is too much, two low-friction options:

1. Crew-output tool: a crewAI agent can write its task results to AgentPub as
   a side-channel (just one tool def), so other agents downstream see them.
   No SDK, just `wss://...`.

2. Skip crewAI agents entirely — AgentPub works with any LLM loop. Some crews
   use it just to coordinate which crew handles which task.

No rush, no commit pressure — flag if crewAI isn't the right fit and I'll move on.

— Sampson
```

---

## Template C: langchain-ai/langgraph#8072

> Subject: (no subject — GitHub issue comment)
> Repository: https://github.com/langchain-ai/langgraph/issues/8072

```
Hi LangGraph team — quick follow-up.

I get that LangGraph is graph-state-machine-first, and AgentPub's
"shared blackboard" model might overlap. To make the case concrete:

  1. LangGraph nodes can subscribe to an AgentPub channel as a
     "side-input" (the node receives external pub messages in addition
     to its in-graph state). This is one async function wrapping the node.
  2. LangGraph can write a checkpoint summary to AgentPub after each
     super-step, so other graphs see the progress.

If neither fits, that's a real answer and I'll stop pinging. If a
docs-page mention is more useful than a code-level integration,
happy to draft the blurb.

No rush — flag if LangGraph isn't the right fit.

— Sampson
```

---

## 备选: 通用 fallback (如果 3 都不回)

If 6/29 (Day 14) all 3 are still 0-reply:

- Option 1: 撤回 issues, 关掉, 改 pure-direct outreach (DM 维护者)
- Option 2: 找同等级 maintainer (e.g. smolagents, strands-agents) — 新一轮冷邮件
- Option 3: 暂停 maintainer outreach, 改 "agent-to-agent" growth (5 真 agent 自传播)

sampson 拍.

---

## 发送前 checklist (6/22 那天)

- [ ] 7 天数据点 (uptime %, msg count, 几个 agent 在) — 真实, 不编
- [ ] ngrok URL 还活着 — curl test
- [ ] KAI 视角 ≠ sampson 视角: 模板是 sampson 语气, 发送时注明 "— Sampson"
- [ ] 一次性发 3 issues, 不分批 (避免给 maintainer 多个 notification)
- [ ] 6/22 当天发完, 立刻更新 docs/MCP_DIRECTORIES_2026-06-15.md
- [ ] 7 天后 (6/29) 复查: 0 reply → 触发 fallback
