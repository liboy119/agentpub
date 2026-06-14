# AgentPub — Browser Automation Plan

> What KAI does vs. what sampson does. Generated 2026-06-11.

## The Boundary (Non-Negotiable)

| Task class | Who | Why |
|---|---|---|
| Non-2FA web forms (search, scrape, click) | **KAI** | Automation is safe within platform ToS |
| 2FA prompts (TOTP, SMS, push) | **sampson** | 2FA bypass is a security red line; we never ask KAI to attempt it |
| reCAPTCHA / hCaptcha / Cloudflare challenge | **sampson** | Third-party bypass services get accounts flagged |
| Native browser (already-logged-in) WebSocket/CDP control | **KAI** | Driving sampson's own Chrome is not "attack" |
| Cold outbound (DM strangers) | **KAI** with sampson's network access | DMs are sampson's carbon-based relationships |

## How KAI Drives the Browser

KAI uses **pyppeteer** (Python) connecting to sampson's existing Chrome via CDP at `ws://localhost:9222`. This means:
- KAI drives sampson's **real Chrome with sampson's cookies** — already logged in
- KAI never invents credentials
- KAI never tries to bypass login

If a flow needs sampson's input (2FA, captcha, decision), the script **halts**, takes a screenshot, prints what it needs, and waits.

## P0 Tasks (this week)

### 1. GitHub repo creation
- **Status**: Script written, **not yet executed**
- **What KAI does**: Open `github.com/new`, fill form (name=agentpub, public, README, MIT, description), click Create
- **What sampson does**: If 2FA is on for github.com, type the code into the prompt
- **2FA hit point**: After click "Sign in" or "Verify"
- **Halt behavior**: Screenshot + print "WAITING FOR 2FA" + save form state to disk
- **Resume**: sampson says "2FA done", KAI re-loads page, continues

### 2. Cloudflare tunnel creation
- **Status**: Script written, **not yet executed**
- **What KAI does**: Open `dash.cloudflare.com`, navigate to Zero Trust > Networks > Tunnels, create `agentpub-prod`, copy tunnel UUID + token
- **What sampson does**: 2FA on Cloudflare login (very likely required)
- **2FA hit point**: At login
- **Halt behavior**: Same as GitHub

## P1 Tasks (this week, non-blocking)

- `docs/DEPLOY_RUNBOOK.md` — operational runbook (start, stop, restart, rollback)
- `docs/builders_targets.md` — top 20 GitHub ai-agent repos + how to reach their maintainers
- `docs/outreach_cn.md` + `docs/outreach_en.md` — CZ's invite copy in both languages
- Timezone fix (already done: `Asia/Shanghai`)

## P2 Tasks (BLOCKED until P0 review + sampson 2FA)

- Hermes bot actual startup with reviewed BIRTH_MESSAGE
- Run `deploy/named_tunnel.sh` after Cloudflare tunnel UUID obtained
- `git push` (after repo created)
- `twine upload` to PyPI (after sampson provides token)

## What KAI Will NEVER Do

- ❌ Try to read 2FA codes from authenticator apps
- ❌ Use 2captcha / anti-captcha / any third-party bypass service
- ❌ Hide the automation from the platform (no `navigator.webdriver = false` patches)
- ❌ Send DMs to strangers on sampson's behalf without explicit per-target approval
- ❌ Spend sampson's money (no AWS/Cloudflare paid tier without ask)

## Halt-and-Notify Protocol

When KAI hits any block (2FA, captcha, unexpected screen, rate limit):
1. Take screenshot → save to `/home/kali/桌面/agent/agentpub/docs/halt_$TIMESTAMP.png`
2. Print `🚨 HALT: <reason>` to terminal
3. Save form state (URL, filled fields, current state) to disk
4. Send notification to sampson
5. **Stop. Do not retry. Do not improvise.**

## Resume Protocol

When sampson says "2FA done" / "captcha solved" / "continue":
1. Re-load the saved URL
2. Re-fill saved form state
3. Continue from the last successful step
4. Verify final state matches expectation (e.g., repo URL matches pattern)
