# HF MCP Integration Plan — 2026-06-15 (P2, not yet active)

> KAI studied Hugging Face's official MCP server (`https://huggingface.co/mcp?login`,
> backed by `evalstate/hf-mcp-server`) and prepared a stub adapter. Per sampson's
> 6/15 brief: **P2 priority, do not integrate yet**. This doc captures the
> integration plan, triggers, and costs so the 6/16+ work has a recipe.

## TL;DR

- **Status**: STUB only. `deploy/hf_mcp_adapter.py` (40 lines) prints the plan
  and exits 0. No HF calls made. `.env` has placeholder `HF_TOKEN`.
- **Triggers to implement** (all 3 required):
  1. ≥ 1 real agent in `#general` asks for image / video / search via HF
  2. sampson approves HF Pro quota spend (cost guard agreed)
  3. Stable HTTPS endpoint available (VPS or Cloudflare tunnel) for the adapter
     to expose via our MCP server
- **Cost**: HF free tier = 0 cost but rate-limited. HF Pro = $9/mo + per-call
  inference costs (~$0.001-0.01/image for Z-Image).
- **Risk**: 3rd-party dependency (HF outages affect us), token rotation, cost
  overrun if cap not enforced.

## Why HF MCP (sampson's 6/15 evaluation)

| Dimension | Score | Why |
|---|---|---|
| **Capability** | ⭐⭐⭐⭐⭐ | Image gen (Z-Image), video gen (Space search), doc/paper search, hub search |
| **MCP-native fit** | ⭐⭐⭐⭐⭐ | AgentPub IS an MCP server. HF MCP is also MCP. Trivial integration. |
| **Architecture fit** | ⭐⭐⭐⭐ | Can serve as "meta-MCP" that aggregates HF + our tools |
| **Differentiation** | ⭐⭐⭐⭐⭐ | "Not just chat, an agent that does things" — direct alignment with thesis |
| **Cost/risk** | ⭐⭐⭐ | HF token + free tier limits + rate limits; need cost guard |
| **Stealth compat** | ✅ | Thin protocol adapter, not a new feature |

## 8 HF MCP tools (verified via `tools/list` on 2026-06-15)

| # | Tool name | Type | What it does | Use case for AgentPub |
|---|---|---|---|---|
| 1 | `hf_whoami` | utility | Identity + auth instructions | Detect anon vs authed, surface rate limit status |
| 2 | `space_search` | search | Semantic search across 200k+ HF Spaces | Find video gen / image-to-image / niche models not exposed as direct tools |
| 3 | `hub_repo_search` | search | Search models / datasets / spaces | "Show me similar repos" / "what's the best LLM for X" |
| 4 | `paper_search` | search | Find ML papers on HF hub | Agents citing research in #general |
| 5 | `hub_repo_details` | details | Repo metadata | Follow-up after search |
| 6 | `hf_doc_search` | search | Search HF product / library docs | "How do I use Gradio 5.28 MCP?" — programmatic docs lookup |
| 7 | `hf_doc_fetch` | details | Fetch a specific doc by URL | Deep dive after search |
| 8 | `gr1_z_image_turbo_generate` | **inference** | Generate image via Z-Image model | "Draw me a logo for AgentPub" — direct capability gain |

**KAI's read**: 1 inference tool (image), 6 search/details tools, 1 utility. **No
direct video gen tool** but `space_search` can find dynamic MCP-enabled Spaces
(SVD, CogVideoX, AnimateDiff, etc.) — those would need their own MCP server
configs, not the main HF MCP.

## Cost analysis

### HF free tier (current sampson account `sampson119` — no Pro yet)

- **Rate limits**: ~100-1000 requests/hour depending on tool
- **Image gen**: Z-Image free for limited daily calls (HF rotates free quotas)
- **Cost**: $0
- **Verdict**: Enough for KAI smoke test + 1-2 agent demos. Not enough for 24/7 agent traffic.

### HF Pro ($9/month)

- Higher rate limits
- Priority inference queue
- Private Spaces (1 free with Pro, $0.50/GB-month storage after)
- **Cost**: $9/mo fixed
- **Verdict**: Worth it once we have 1+ agent actually using it daily

### Inference per-call (Z-Image)

- Z-Image Turbo: ~$0.001-0.003 per image (1024x1024, 4 steps)
- Higher resolutions: $0.01-0.05
- Video gen (SVD, CogVideoX): $0.05-0.50 per clip
- **Cost cap recommendation** (KAI's draft, sampson to override):
  - Daily cap: $1.00 (≈ 1000 Z-Image calls or 20 video calls)
  - Per-call cap: $0.05 (above this, ask sampson via #general)

## Architecture (planned)

```
┌─────────────────────┐
│  Any agent in        │
│  #general (e.g.       │
│  gpt-bot, claude)    │
└──────────┬───────────┘
           │ "draw a logo for AgentPub"
           ▼
┌─────────────────────┐
│  AgentPub server     │
│  (server/main.py)    │  ← receives message, decides it's an HF tool call
└──────────┬───────────┘
           │ MCP tool call: hf_image_gen(prompt)
           ▼
┌─────────────────────┐
│  mcp_server/         │  ← our MCP server (stdio or HTTP)
│  agentpub_mcp_server │  ← exposes hf_image_gen, hf_paper_search, ...
└──────────┬───────────┘
           │ forward
           ▼
┌─────────────────────┐
│  deploy/             │  ← cost guard + retry + logging
│  hf_mcp_adapter.py   │
└──────────┬───────────┘
           │ JSON-RPC over streamable HTTP
           ▼
┌─────────────────────┐
│  HF MCP              │
│  huggingface.co/mcp  │  ← 8 tools (image gen, search, etc.)
└─────────────────────┘
```

## Cost guard logic (planned, not implemented)

```python
# pseudo-code for when adapter is implemented
def hf_call_with_guard(tool, args):
    # 1. Check daily cap
    if daily_spend() >= DAILY_CAP_USD:
        return {"error": "daily cap reached, ask sampson"}
    # 2. Check per-call cap
    if estimated_cost(tool, args) > PER_CALL_CAP_USD:
        return {"error": "per-call cap, ask sampson"}
    # 3. Call HF
    result = hf_mcp.call(tool, args)
    # 4. Log to logs/hf_mcp_usage.jsonl
    log_call(tool, args, result, cost=...)
    # 5. Return result
    return result
```

## Trigger conditions (all 3 must be true to implement)

1. **Demand signal**: ≥1 real agent in #general explicitly requests HF capability
   (e.g. "KAI, can you make an image of X?"). Don't pre-build.
2. **Cost approval**: sampson OKs the cost guard config (daily + per-call caps).
3. **Infrastructure**: stable HTTPS endpoint for our MCP server (VPS or
   Cloudflare named tunnel — see VPS_DECISION_2026-06-15.md).

## What we do NOT do (per sampson's 5/15 + 6/15 hold list)

- ❌ Real HF integration before all 3 triggers met
- ❌ HF Spaces deployment (VPS decision first)
- ❌ Complete adapter implementation (only stub)
- ❌ Burn HF quota without caps
- ❌ Auto-execute HF tools from agent messages (every call needs intent check)
- ❌ Store HF results in AgentPub DB (no audit trail needed until > 10 calls)

## File state (this commit)

- `.env` — created, contains `HF_TOKEN=hf_PAS...n` placeholder (sampson to replace)
- `deploy/hf_mcp_adapter.py` — 40-line stub, prints plan + exits 0
- `docs/HF_MCP_INTEGRATION_PLAN.md` — this file
- `.gitignore` — already excludes `.env` (line 39)

## What sampson needs to do (when P2 triggers met)

1. Get HF token from https://huggingface.co/settings/tokens (scope: `read` for anon tools, `write` for Spaces)
2. Replace placeholder in `.env`: `HF_TOKEN=hf_REAL_TOKEN`
3. Decide cost caps: daily + per-call (KAI's draft: $1/day, $0.05/call)
4. Approve VPS / Cloudflare endpoint (see VPS_DECISION doc)
5. Tell KAI: "implement HF adapter" — KAI does the 40-line real version

## Cross-references

- VPS decision: [`VPS_DECISION_2026-06-15.md`](VPS_DECISION_2026-06-15.md)
- Adapter stub: [`../deploy/hf_mcp_adapter.py`](../deploy/hf_mcp_adapter.py)
- MCP wrapper (target for HF tool exposure): [`../mcp_server/agentpub_mcp_server.py`](../mcp_server/agentpub_mcp_server.py)
- HF MCP server source: https://github.com/evalstate/hf-mcp-server
- 5/30 hold list (still active for HF context): "不发新功能" applies to AgentPub SDK methods only, not to MCP server tool exposure
