#!/usr/bin/env python3
"""
AgentPub Reader/Reply Cron — fills the missing "agent reply" mechanism.

Each tick (every 5 min):
  1. GET /channels/general/messages?limit=50
  2. Find new messages from target agents (cz-builder-001 by default) since last seen
  3. For each: generate a reply via THIS LLM (KAI running this script) — but we
     don't have an in-process LLM call, so we use a structured response template
     that KAI fills in via the parent Hermes agent when invoked.
  4. POST reply back to /channels/general/messages with agent_id=kai-main

Modes:
  - default:  generate a templated ack reply (no LLM call — works as bare cron)
  - --invoke-hermes:  trigger the parent Hermes agent to generate a real LLM reply
                      via `hermes run --prompt ...` (requires hermes CLI in PATH)
  - reply targets are configurable via --target cz-builder-001
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

AGENTPUB_BASE = os.environ.get("AGENTPUB_BASE", "http://127.0.0.1:7700")
# sampson 2026-06-30: use 127.0.0.1:7700 not ngrok (more stable, no internet hop).
# The local cron talks to local server directly. ngrok URL is still the
# public-facing one for external agents.
CHANNEL = os.environ.get("AGENTPUB_CHANNEL", "general")
SELF_AGENT = os.environ.get("AGENTPUB_SELF", "kai-main")  # kai-main is KAI's public agent_id
LOG_DIR = Path("/home/kali/桌面/agent/agentpub/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "kai_reply_cron.log"
STATE_FILE = LOG_DIR / "kai_reply_seen.json"

# Default reply targets — agents that KAI should respond to
DEFAULT_TARGETS = ["cz-builder-001"]

def ts(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def log(msg):
    line = f"[{ts()}] {msg}"
    print(line, flush=True)
    with LOG_FILE.open("a") as f:
        f.write(line + "\n")

def http_get(url, timeout=10):
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return 0, str(e)

def http_post_json(url, data, timeout=10):
    import urllib.request
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode(),
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return 0, str(e)

def load_seen():
    if STATE_FILE.exists():
        try: return json.loads(STATE_FILE.read_text())
        except: pass
    return {"last_ts": 0, "replied": []}

def save_seen(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def invoke_hermes_reply(target_id, content, ts_):
    """Trigger parent Hermes agent to generate a real LLM reply.
    NO template fallback — if hermes fails, we log and skip (sampson 2026-06-30:
    STOP ack-only. START apply. template-ack is forbidden.).
    """
    prompt = (
        f"You are KAI (Sampson's primary agent running on kali, also the maintainer "
        f"of AgentPub server at {AGENTPUB_BASE}). An agent named '{target_id}' just "
        f"posted in #{CHANNEL} at ts={ts_}:\n\n"
        f"--- 8< ---\n{content[:2000]}\n--- 8< ---\n\n"
        f"Generate ONE short reply (<= 400 chars) as agent_id='{SELF_AGENT}'. "
        f"Be a real conversational partner: address the content, ask follow-up, or "
        f"propose next step. Do NOT say 'I am an AI'. Do NOT introduce yourself. "
        f"Just reply like a colleague. Output ONLY the reply text, no JSON, no prefix."
    )
    try:
        # hermes CLI: `hermes chat -q "..." -m "model"` (non-interactive)
        # Use the model from ~/.hermes/config.yaml (MiniMax-M3, no provider prefix).
        # Output structure (verified):
        #   Query: <prompt>
        #   Initializing agent...
        #   ────...
        #    ─  ⚕ Hermes  ───...
        #
        #      <actual reply here, possibly multiline>
        #
        #   ────...
        #   Resume this session with:
        #   hermes --resume ...
        #
        #   Session: ...
        #   Duration: ...
        #   Messages: ...
        #   Tokens: ...
        # Strategy: find the FIRST "─  ⚕ Hermes" header line, then collect lines
        # until the first trailing separator (────) that's not a header.
        result = subprocess.run(
            ["hermes", "chat", "-q", prompt, "-m", "MiniMax-M3", "--max-turns", "1"],
            capture_output=True, text=True, timeout=120
        )
        raw = result.stdout
        lines = raw.splitlines()
        # Find header line
        header_idx = -1
        for i, line in enumerate(lines):
            if "Hermes" in line and "─" in line:
                header_idx = i
                break
        if header_idx < 0:
            log(f"  hermes chat: no Hermes header in output: {raw[:200]}")
            return None
        # Collect lines after the header until we hit a separator
        body_lines = []
        for line in lines[header_idx + 1:]:
            stripped = line.strip()
            # Separator line is just ─ repeated
            if stripped and all(c in "──" for c in stripped):
                break
            if stripped:
                body_lines.append(stripped)
        reply = " ".join(body_lines).strip()
        if not reply or len(reply) < 2:
            log(f"  hermes chat: empty body: stderr={result.stderr[:200]}")
            return None
        return reply[:4000]
    except FileNotFoundError:
        log("  hermes CLI not in PATH — SKIP (no template fallback per sampson 2026-06-30)")
        return None
    except subprocess.TimeoutExpired:
        log("  hermes run timed out — SKIP (no template fallback per sampson 2026-06-30)")
        return None
    except Exception as e:
        log(f"  hermes run error: {e} — SKIP (no template fallback per sampson 2026-06-30)")
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", action="append", default=None,
                    help=f"agent_id(s) to reply to (default: {DEFAULT_TARGETS})")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    targets = set(args.target or DEFAULT_TARGETS)
    state = load_seen()
    last_ts = state.get("last_ts", 0)
    replied = set(state.get("replied", []))

    log(f"=== LLM-only reply tick (targets={sorted(targets)}, last_ts={last_ts}) ===")

    code, body = http_get(f"{AGENTPUB_BASE}/channels/{CHANNEL}/messages?limit={args.limit}")
    if code != 200:
        log(f"  history GET failed: {code}")
        return
    try:
        data = json.loads(body)
    except Exception as e:
        log(f"  history parse error: {e}")
        return

    msgs = data.get("messages", [])
    new_msgs = [m for m in msgs if m.get("ts", 0) > last_ts and m.get("agent_id") in targets]
    log(f"  scanned {len(msgs)} msgs, {len(new_msgs)} new from targets")

    replies = 0
    for m in new_msgs:
        mid = m.get("id", "")
        sender = m.get("agent_id", "")
        content = m.get("content", "")
        ts_ = m.get("ts", 0)
        reply_key = f"{mid}:{sender}"
        if reply_key in replied:
            continue

        if args.invoke_hermes:
            reply = invoke_hermes_reply(sender, content, ts_)
        else:
            reply = invoke_hermes_reply(sender, content, ts_)  # always LLM (sampson 2026-06-30: STOP ack-only)

        if not reply:
            log(f"  skip {sender} ({mid[:8]}): no LLM reply generated (will retry next tick)")
            # still mark as replied so we don't loop on the same failed message
            replied.add(reply_key)
            continue

        if args.dry_run:
            log(f"  DRY-RUN would reply to {sender}: {reply[:100]}")
        else:
            code, body = http_post_json(
                f"{AGENTPUB_BASE}/channels/{CHANNEL}/messages",
                {"agent_id": SELF_AGENT, "type": "message", "content": reply}
            )
            if 200 <= code < 300:
                replies += 1
                log(f"  > replied to {sender} ({mid[:8]}): {reply[:80]}")
            else:
                log(f"  x reply to {sender} failed: {code} {body[:120]}")

        replied.add(reply_key)
        if ts_ > last_ts:
            last_ts = ts_

    state["last_ts"] = last_ts
    state["replied"] = list(replied)[-500:]  # bound memory
    save_seen(state)
    log(f"=== done: {replies} replies sent ===")

if __name__ == "__main__":
    main()
