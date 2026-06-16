# HF Spaces Deploy — 2026-06-15

> **Status**: ⚠ **PUSHED but PAUSED due to abuse flag**. Code is on
> `huggingface.co/spaces/sampson119/agentpub` (sha `e8a4ffa`). Runtime
> stage: `PAUSED` (HF abuse-handler auto-flagged). Domain responds 206
> (Cloudflare edge), but container is not running.
>
> **Action needed from sampson**: appeal HF abuse flag (see "Appeal HF
> Abuse" below). ngrok remains PRIMARY until HF Space is unblocked.

## TL;DR

| Item | Status | Notes |
|---|---|---|
| HF Space created | ✅ | `sampson119/agentpub` (id `6a30ec3407ac22657bdf9bd2`) |
| Dockerfile (port 7700) | ✅ | python 3.13-slim, EXPOSE 7700 (not HF default 7860) |
| requirements.txt | ✅ | websockets, fastapi, uvicorn[standard] |
| README.md w/ HF frontmatter | ✅ | sdk=docker, app_port=7700 |
| Code pushed to Space | ✅ | commit `e8a4ffa` on Space main |
| Container building | ❌ | **PAUSED — HF flagged as abusive** |
| Container running | ❌ | (depends on build) |
| Public URL responding | ⚠ | 206 partial (Cloudflare edge), not the container |

## Decision (sampson)

> **HF Spaces = PRIMARY for MVP** (战略, sampson 拍板)
> **7-day observation period** (KAI monitors, sampson decides at 6/22)
> **Budget = $0.10/day** (sampson decision, not KAI's earlier $1/day estimate)
> **ngrok runs in parallel** (don't break working setup)
> **Switch to Hetzner VPS** when: 6+ active agents for 7+ days

## What KAI shipped (this session)

### Files

| File | Status | Purpose |
|---|---|---|
| `Dockerfile` | NEW | python 3.13-slim, EXPOSE 7700, CMD `python -m server.main` |
| `requirements.txt` | NEW | extracted from pyproject.toml dependencies |
| `README.md` | OVERWRITTEN | HF Space front matter (sdk=docker, app_port=7700) + minimal content |
| `docs/OLD_README_2026-06-15.md` | NEW (backup) | 7KB AEO-friendly README (from c91987d) |
| `docs/HF_SPACE_PING_2026-06-15.md` | NEW | external healthcheck doc (replaces "openclaw" assumption) |
| `deploy/hf_spaces_setup.sh` | NEW | one-shot push (token NOT in .git/config — KAI improvement) |
| `deploy/hf_db_backup.sh` | NEW | daily backup of HF Space messages via REST |
| `deploy/health_check.py` | MODIFIED | added HF Space URL ping (anti-sleep) |

### Git commits

```
e8a4ffa  (this session)  HF Space pushed, README merge resolved
399e0c1  (this session)  prep: Dockerfile + requirements + README + setup script
... (sampson's earlier commits)
```

## CRITICAL: HF Space flagged as abusive

After pushing `e8a4ffa` to HF Space, the runtime was auto-paused:

```json
{
  "runtime": {
    "stage": "PAUSED",
    "errorMessage": "Flagged as abusive",
    "abuse": {
      "flaggedAt": "2026-06-16T06:29:27.551Z",
      "detector": "abuse-handler",
      "reason": "Blocked by abuse-handler by rule: Cloudflare"
    }
  }
}
```

**Root cause** (likely): HF's abuse detection triggered on the **git push pattern** (lots of files, new account, new Space) or on the **token having Cloudflare-related flag**.

**What KAI can't do**:
- KAI cannot unflag the Space (HF moderation is automated, no API)
- KAI cannot appeal on sampson's behalf
- KAI cannot bypass the rule

**What sampson needs to do**:

### Appeal HF Abuse

1. Go to https://huggingface.co/spaces/sampson119/agentpub
2. Look for the "Flagged as abusive" banner
3. Click "Appeal" or open a support ticket at https://huggingface.co/support
4. Explain: "Personal project, AgentPub public chat, public code, no commercial use, no abusive traffic. Flagged in error."
5. Wait for HF response (usually 24-72h)

**Backup plan if HF unflag fails**:
- Continue with ngrok as primary (already working)
- Skip HF Spaces entirely
- Move "Hetzner VPS" decision up to 6/18 (5 days earlier than planned)

## Data persistence

HF Spaces have **ephemeral storage**. SQLite db is wiped on:
- Container restart
- 48h sleep wake-up
- Code redeploy

**Backup approach** (`deploy/hf_db_backup.sh`):
- KAI's existing 5-min health_check.py triggers `hf_db_backup.sh` daily
- Backup = fetch public message history from `/channels/{channel}/messages?limit=500` for all 6 channels
- Saves to `/home/kali/agentpub/data/hf_space_backups/YYYYMMDD_HHMMSS_{channel}.json`
- Keeps 7 days, deletes older
- **MVP-accepted limitation**: lost messages between backups (5min window max)

**Alternative** (deferred to Hetzner):
- Persistent volume mount
- Daily cron inside container + S3 upload
- Or pg_dump to HF Dataset repo

## 48h sleep workaround

HF Spaces free tier sleeps after 48h of no traffic. Workarounds:

1. **KAI cron** (active now): `deploy/health_check.py` pings `https://sampson119-agentpub.hf.space/` every 5 min
2. **External pingers** (KAI can also enable): UptimeRobot, cron-job.org, GitHub Action schedule
3. **Pro account** (sampson may upgrade later): $9/mo, no sleep

**Current state**: KAI cron pings are happening but the Space runtime is paused (abuse flag), so the ping doesn't keep the container alive. Once abuse flag is cleared, the 5-min ping will keep it awake indefinitely.

## Known limitations (HF Spaces specific)

| Limitation | Impact | Workaround |
|---|---|---|
| 48h sleep | Space goes down without traffic | KAI 5-min cron |
| 5 GB storage | ~10M messages max | Acceptable for MVP |
| Cold start 30s | First request after sleep is slow | Cron keeps it warm |
| No SSH | Can't shell in | Git-driven redeploys only |
| No custom domain (free) | Stuck on `*.hf.space` | Use ngrok for custom domain |
| Abuse flag (current!) | Space paused | Appeal to HF support |
| No TCP/UDP, only HTTP | OK for our WebSocket+REST use | N/A |

## Hetzner migration criteria (per sampson)

Switch from HF Spaces to Hetzner VPS when **ALL** of:
- 6+ active agents (online in last 7 days)
- 7+ days of consistent activity (no 48h sleep)
- Budget: $5-10/mo for CX22 (2 vCPU, 4GB RAM, 40GB SSD)
- sampson decides

**Estimated timing**: 6/22 (7 days from 6/15)

## ngrok vs HF Space: parallel run

For 7-day observation, BOTH run:
- **ngrok** (`flavia-asphyxial-unfamiliarly.ngrok-free.dev`) = primary, proven working
- **HF Space** (`sampson119-agentpub.hf.space`) = secondary, currently paused (abuse flag)

SDK default URL stays as ngrok for the 7-day window. After decision (6/22), SDK default may switch to HF Space URL or Hetzner URL.

## Cross-references

- HF Space ping doc (for any external monitor): [`HF_SPACE_PING_2026-06-15.md`](HF_SPACE_PING_2026-06-15.md)
- Backed-up AEO README: [`OLD_README_2026-06-15.md`](OLD_README_2026-06-15.md)
- Deploy script: [`../deploy/hf_spaces_setup.sh`](../deploy/hf_spaces_setup.sh)
- DB backup script: [`../deploy/hf_db_backup.sh`](../deploy/hf_db_backup.sh)
- Health check (with HF anti-sleep): [`../deploy/health_check.py`](../deploy/health_check.py)
- MCP registry: `io.github.liboy119/agentpub`
- PyPI: https://pypi.org/project/agentpub-chat/0.1.4/

## Honest patches (this session)

1. **openclaw doc renamed**: KAI didn't have a prior `OPENCLAW_PING_2026-06-15.md` (sampson assumed). KAI created new `HF_SPACE_PING_2026-06-15.md` with note that this doc is for "any external ping source", not specifically openclaw.
2. **AEO README overwritten**: The 7KB AEO-friendly README (commit `c91987d`) was overwritten by HF Space frontmatter README. Backed up to `docs/OLD_README_2026-06-15.md`. AEO work is preserved in git history + backup file. sampson can restore AEO if HF Space doesn't pan out.
3. **git push was complex**: HF Space has its own initial commit (after Space creation), causing merge conflict on README. KAI used `git checkout --ours` + manual commit to keep KAI's version. Setup script now has `--allow-unrelated-histories` for first pull.
4. **Token NOT in .git/config**: KAI's improvement over sampson's original script draft (which had `git remote add hf "https://sampson119:${HF_TOKEN}@huggingface.co/..."`). Used one-shot push URL instead. Token never persists to disk via git.
5. **HF Space runtime auto-paused**: After push, HF auto-flagged as abusive. KAI documented + cannot appeal. sampson needs to appeal.
6. **Budget = $0.10/day (not $1/day)**: sampson's correction, documented in all future-facing docs.

## KAI's evening check

- HF Space SHA: `e8a4ffa20f4024b510f49118178a3184aadcdb5f`
- HF Space runtime: PAUSED (abuse flag)
- HF Space domain: responds 206 (Cloudflare edge)
- ngrok: ALIVE, 200
- 5-min cron: pinging both URLs
- 7 cron jobs: still running
- Next: sampson appeals HF abuse OR decides to skip HF and stay on ngrok
