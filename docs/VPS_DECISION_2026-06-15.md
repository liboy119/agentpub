# VPS Decision — 2026-06-15 (P2, awaiting sampson pick)

> KAI compared 3 deployment targets for AgentPub. Recommendation:
> **Oracle Cloud Free Tier first (5 min test), Hetzner CX22 as fallback,
> HF Spaces as P3 backup.** Decision needed before HF MCP integration
> (P2 trigger #3) and before any HTTPS endpoint exposure (smithery / HF).

## TL;DR

| Candidate | Cost (1st year) | Stability | Time-to-deploy | KAI recommendation |
|---|---|---|---|---|
| **Oracle Cloud Free Tier** | **$0** (Always Free ARM 4-core 24GB) | High (real cloud) | 5 min signup + 30 min OS setup | 🥇 **Try first** |
| Hetzner CX22 | ~$4.50/mo (~$54/yr) | Highest (datacenter-grade) | 1 hour | 🥈 Fallback if Oracle's free tier is over-subscribed |
| HF Spaces (Docker) | $0-9/mo (CPU free, GPU $0.60/hr) | Medium (cold start) | 30 min via git push | 🥉 P3 backup only — best for demos, not 24/7 |

**Oracle is the clear winner for a solo developer's MVP**: 4 ARM cores, 24 GB
RAM, 200 GB storage, **free forever** (not a trial). 5-min signup if sampson
hasn't used Oracle Cloud before.

## Why we need a VPS at all (context)

Current state:
- **Local Kali** (sampson's box): runs AgentPub server on `localhost:7700`
- **Public URL**: `https://flavia-asphyxial-unfamiliarly.ngrok-free.dev` (ngrok free, ephemeral)
- **MCP server**: stdio only (works, but no remote clients can connect)

What we need next (P2 triggers + MCP distribution):
1. **Stable HTTPS endpoint** for the stdio MCP wrapper (smithery requires HTTP)
2. **Stable URL** so mcp.directory / glama / HF MCP can link to our public server
3. **Persistent storage** for a real DB (currently SQLite, OK for MVP)
4. **Outbound HTTPS to HF MCP** (Kali can already do this, but VPS is more reliable)

## Comparison

### 🥇 Oracle Cloud Free Tier (recommended)

- **Specs** (Always Free, ARM Ampere A1):
  - 4 OCPU (ARM cores)
  - 24 GB RAM
  - 200 GB block storage
  - 10 TB outbound/month
  - Ubuntu 22.04 LTS image
- **Cost**: **$0 forever** (truly free, not trial)
- **Time to deploy**: 5 min signup + 30 min install (apt + Python venv + uvicorn + systemd service)
- **KAI deploy path** (already exists): `deploy/deploy_to_vps.sh` — generic, works for Oracle
- **Pros**:
  - Free forever, not "free for 12 months" like AWS / Azure
  - Real cloud IP (not residential, not ngrok)
  - 24/7 uptime
  - Native ARM Ampere, fast enough for AgentPub's WebSocket server
  - sampson can attach a free subdomain via Cloudflare (sampson has Cloudflare account per memory)
- **Cons**:
  - Oracle signup is sometimes slow / requires phone verification
  - "Always Free" instances can be reclaimed if idle (Oracle policy: must use within 60 days or capacity rules)
  - Not in mainland China (latency issue if any user is in CN)

**Risk**: 10-20% chance Oracle's free tier signup is unavailable in sampson's region, or capacity is full. 5 min to find out.

**KAI deploy estimate**: 30 min once Oracle account ready (sampson pastes API token, KAI runs deploy script).

### 🥈 Hetzner Cloud CX22 (fallback)

- **Specs** (paid, ~€4.35/month):
  - 2 vCPU (x86 Intel)
  - 4 GB RAM
  - 40 GB SSD
  - 20 TB outbound/month
  - Ubuntu 22.04 LTS
- **Cost**: ~$4.50/mo = $54/yr (less if sampson uses existing credits)
- **Time to deploy**: 5 min via hcloud API + 30 min install
- **Pros**:
  - Hetzner is reliable, German datacenter, low latency to EU
  - x86 (more software compatibility vs Oracle ARM)
  - Snapshot + restore built-in
  - No capacity issues
- **Cons**:
  - Costs money (sampson is currently bootstrap mode per memory)
  - Only EU / US / Singapore (no CN)
  - x86 = 1.5x the cost of equivalent ARM for the same workload

**KAI deploy estimate**: 30 min, same script as Oracle.

### 🥉 HF Spaces (Docker) — P3 backup

- **Specs** (free CPU or paid GPU):
  - 2 vCPU (free, slow)
  - 16 GB RAM
  - 50 GB storage
  - Cold start (sleeps after 48h no traffic on free tier)
- **Cost**: $0 (CPU) to $0.60/hr (A10G GPU)
- **Time to deploy**: 30 min via `git push` to a HF Space with `Dockerfile`
- **Pros**:
  - Zero ops — HF handles restarts, HTTPS, subdomain (`*.hf.space`)
  - Git push deploy
  - Direct integration with HF MCP server (same auth)
- **Cons**:
  - **Cold start** on free tier (request → 30-60s delay while container wakes)
  - HF Spaces sleep policy is unpredictable
  - Less control over OS
  - No persistent storage (SQLite dies on restart)
  - Tightly couples AgentPub to HF — defeats the "agent-first internet, no single host" thesis

**KAI verdict**: Good for **demo / showcase** (the "try AgentPub in 30 seconds" path). Bad for **production / 24/7**.

## Recommendation logic

1. **Try Oracle Cloud Free first** (5 min signup test)
2. If Oracle signup fails or capacity is full → **Hetzner CX22** (sampson pays $4.50/mo)
3. If sampson wants zero-cost demo path → **HF Spaces** as a "press to try" button alongside the main deployment

The 3 are not mutually exclusive: sampson can do Oracle as production + HF Spaces as demo button. But Oracle alone covers 95% of needs.

## Concrete next steps (after sampson decides)

### If Oracle Cloud Free

```bash
# 1. sampson signs up at https://cloud.oracle.com/ (5 min, may need credit card for verification but no charge)
# 2. Generate API token at https://cloud.oracle.com/identity/domains/my-profile/api-keys
# 3. sampson pastes token to KAI (similar to PyPI token pattern)
# 4. KAI runs:
oci setup config   # one-time, paste user OCID + tenancy OCID
bash deploy/deploy_to_vps.sh oracle   # creates VM, runs setup, exposes on https://agentpub.sampson.de5.net
```

Total: 30-40 min.

### If Hetzner CX22

```bash
# 1. sampson signs up at https://www.hetzner.com/cloud (5 min)
# 2. Generate API token at https://console.hetzner.cloud/projects/<project>/security/tokens
# 3. sampson pastes token to KAI
# 4. KAI runs:
hcloud server create --name agentpub-prod --type cx22 --image ubuntu-22.04
bash deploy/deploy_to_vps.sh hetzner
```

Total: 30-40 min.

### If HF Spaces (demo path)

```bash
# 1. sampson has HF account (sampson119, confirmed 6/15)
# 2. KAI creates a Space at https://huggingface.co/new-space (Docker SDK)
# 3. KAI pushes Dockerfile + server code
# 4. KAI tests cold start time
```

Total: 30 min, but cold start is a known UX hit.

## Cost-vs-speed matrix

```
                    | Oracle Free | Hetzner CX22 | HF Spaces
Cost (1st year)     |   $0        |   $54        | $0 (CPU)
Time to deploy      |   40 min    |   40 min     | 30 min
Cold start          |   No        |   No         | YES (30-60s)
HTTPS subdomain     |   Manual    |   Manual     | Auto (*.hf.space)
Persistent storage  |   Yes       |   Yes        | No (SQLite dies)
24/7 uptime         |   Yes       |   Yes        | Maybe
Independent of HF   |   Yes       |   Yes        | No
```

## What sampson needs to do

1. **Pick one** (or say "try Oracle first, Hetzner fallback")
2. **Create account** (5 min)
3. **Paste API token** to KAI (similar to PyPI token pattern)
4. **Wait 30-40 min** while KAI runs the deploy script
5. **Verify** by hitting the new HTTPS URL

KAI handles everything else.

## Cross-references

- HF integration plan: [`HF_MCP_INTEGRATION_PLAN.md`](HF_MCP_INTEGRATION_PLAN.md)
- Smithery submission (needs VPS for HTTP endpoint): [`SMITHERY_2026-06-15.md`](SMITHERY_2026-06-15.md)
- Existing VPS deploy script: [`../deploy/deploy_to_vps.sh`](../deploy/deploy_to_vps.sh)
- Existing Cloudflare named tunnel config: `~/.hermes/config.yaml` (per memory, sampson has `agentpub-prod` configured)
- ngrok free URL (current public): `https://flavia-asphyxial-unfamiliarly.ngrok-free.dev`
