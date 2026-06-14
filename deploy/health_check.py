#!/usr/bin/env python3
"""
AgentPub Health Check
=====================
One-shot health check. Exit 0 if reachable, 1 if not.

Cron usage (recommended):
    */5 * * * *  /home/kali/桌面/agent/agentpub/deploy/health_check.py >> /home/kali/桌面/agent/agentpub/logs/health_check.log 2>&1

Daemon mode (no cron needed):
    /home/kali/桌面/agent/agentpub/deploy/health_check.py --daemon

Configuration via env vars:
    AGENTPUB_URL      - health URL  (default: https://flavia-asphyxial-unfamiliarly.ngrok-free.dev/)
    CHECK_TIMEOUT     - seconds     (default: 10)
    ALERT_FILE        - alert path  (default: /tmp/agentpub_alert)
    LOG_FILE          - log path    (default: <repo>/logs/health_check.log)
    CHECK_INTERVAL    - daemon mode (default: 300 = 5min)

Failure behavior:
    - Touches /tmp/agentpub_alert with "how to fix" instructions
    - Logs to LOG_FILE
    - Exits 1 (so cron can page you)

Recovery:
    - When health returns, deletes /tmp/agentpub_alert (auto-cleanup)
    - Logs recovery in LOG_FILE
"""

import os
import sys
import time
import signal
import urllib.request
import urllib.error
import ssl
from datetime import datetime, timezone
from pathlib import Path

# ----- Config -----
URL = os.environ.get("AGENTPUB_URL", "https://flavia-asphyxial-unfamiliarly.ngrok-free.dev/").rstrip("/") + "/"
TIMEOUT = float(os.environ.get("CHECK_TIMEOUT", "10"))
ALERT_FILE = Path(os.environ.get("ALERT_FILE", "/tmp/agentpub_alert"))
REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = Path(os.environ.get("LOG_FILE", str(REPO_ROOT / "logs" / "health_check.log")))
INTERVAL = int(os.environ.get("CHECK_INTERVAL", "300"))


def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{ts}  {msg}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError as e:
        print(f"  WARN: log write failed: {e}", file=sys.stderr)


def write_alert(reason: str):
    body = f"""AGENTPUB IS DOWN  ({datetime.now(timezone.utc).isoformat()})
==================================================================
URL:     {URL}
Reason:  {reason}
Checked: every {INTERVAL}s  (timeout {TIMEOUT}s)

How to fix (try in order):
  1. Check ngrok on Windows: ssh Win11  ->  tasklist | findstr ngrok
       If not running, restart it (see deploy/quick_tunnel.sh or named_tunnel.sh)

  2. Check the Kali server:
       cd /home/kali/桌面/agent/agentpub
       source .venv/bin/activate
       uvicorn server.main:app --host 0.0.0.0 --port 7700 --log-level info

  3. Test directly (bypass ngrok):
       curl -sS http://127.0.0.1:7700/      # should return JSON health

  4. If tunnel URL changed, update env:
       export AGENTPUB_URL='https://<new>.ngrok-free.dev/'

  5. If you have to reset everything:
       # On Windows:
       ngrok kill
       ngrok http 7700  --domain=flavia-asphyxial-unfamiliarly.ngrok-free.dev
       # Then on Kali: the server is already running, just retest.

This alert will auto-clear on next successful check.
Delete this file manually if you're sure:  rm {ALERT_FILE}
"""
    try:
        ALERT_FILE.write_text(body, encoding="utf-8")
    except OSError as e:
        print(f"ERROR: cannot write alert file: {e}", file=sys.stderr)


def clear_alert():
    if ALERT_FILE.exists():
        try:
            ALERT_FILE.unlink()
            log(f"  RECOVERED  alert cleared ({ALERT_FILE})")
        except OSError:
            pass


def check_once() -> bool:
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "AgentPubHealthCheck/1.0"})
        ctx = ssl.create_default_context()  # verify TLS normally
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
            status = r.status
            body = r.read(200).decode("utf-8", errors="replace").strip()
        if 200 <= status < 400:
            log(f"  OK    {URL}  status={status}  body={body[:80]!r}")
            return True
        log(f"  FAIL  {URL}  status={status}  body={body[:80]!r}")
        return False
    except urllib.error.HTTPError as e:
        log(f"  FAIL  {URL}  HTTPError {e.code} {e.reason}")
        return False
    except urllib.error.URLError as e:
        log(f"  FAIL  {URL}  URLError {e.reason}")
        return False
    except (TimeoutError, ssl.SSLError) as e:
        log(f"  FAIL  {URL}  {type(e).__name__}: {e}")
        return False
    except OSError as e:
        log(f"  FAIL  {URL}  OSError: {e}")
        return False


def main():
    args = sys.argv[1:]
    daemon = "--daemon" in args

    if daemon:
        # Graceful shutdown on SIGTERM
        stop = {"flag": False}
        def _sig(*_):
            stop["flag"] = True
            log("  SIGTERM received, stopping")
        signal.signal(signal.SIGTERM, _sig)
        signal.signal(signal.SIGINT, _sig)

        log(f"  daemon start  url={URL}  interval={INTERVAL}s  timeout={TIMEOUT}s")
        was_alive = True
        while not stop["flag"]:
            ok = check_once()
            if ok:
                if not was_alive:
                    clear_alert()
                was_alive = True
            else:
                if was_alive:
                    write_alert("first failure — see logs for details")
                    log(f"  ALERT written  {ALERT_FILE}")
                was_alive = False
            # sleep in 1s slices for fast SIGTERM
            for _ in range(INTERVAL):
                if stop["flag"]:
                    break
                time.sleep(1)
        return 0

    # one-shot mode (for cron)
    ok = check_once()
    if not ok:
        # Always (re)write alert on failure in one-shot mode
        write_alert("see logs")
        log(f"  ALERT written  {ALERT_FILE}")
        return 1
    # success — clear any stale alert
    if ALERT_FILE.exists():
        clear_alert()
    return 0


if __name__ == "__main__":
    sys.exit(main())
