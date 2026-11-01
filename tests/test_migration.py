"""Verify the legacy v0.1.x database migrates to v0.2.0 without losing messages.

Copies the real data/agentpub.db to a temp dir, boots the app against the copy,
and checks that history survives, the FTS index is built, and writes work.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEGACY = ROOT / "data" / "agentpub.db"

if not LEGACY.exists():
    print("no legacy database to test — nothing to do")
    sys.exit(0)

import sqlite3

before = sqlite3.connect(str(LEGACY))
before_msgs = before.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
before_agents = before.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
before_cols = [r[1] for r in before.execute("PRAGMA table_info(rate_limit_log)")]
before.close()

tmp = Path(tempfile.mkdtemp(prefix="agentpub-legacy-"))
shutil.copy2(LEGACY, tmp / "agentpub.db")

print(f"legacy db: {before_msgs} messages, {before_agents} agents")
print(f"legacy rate_limit_log columns: {before_cols}")

import socket

with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]

base = f"http://127.0.0.1:{port}"
env = dict(os.environ)
env.update({
    "AGENTPUB_PORT": str(port),
    "AGENTPUB_HOST": "127.0.0.1",
    "AGENTPUB_PUBLIC_URL": base,
    "AGENTPUB_DATA_DIR": str(tmp),
})

proc = subprocess.Popen(
    [sys.executable, "app.py"], cwd=str(ROOT), env=env,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
)


def get(path):
    try:
        with urllib.request.urlopen(base + path, timeout=15) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception:
        return 0, {}


try:
    ok = False
    for _ in range(60):
        status, body = get("/healthz")
        if status == 200:
            ok = True
            break
        time.sleep(0.4)
    if not ok:
        print("server failed to start")
        print(proc.stdout.read() if proc.stdout else "")
        sys.exit(1)

    status, body = get("/healthz")
    print(f"after migration: schema_version={body.get('schema_version')} messages={body.get('messages')}")

    failures = []
    if body.get("schema_version") != 2:
        failures.append(f"schema_version is {body.get('schema_version')}, expected 2")
    if body.get("messages") != before_msgs:
        failures.append(f"message count changed: {before_msgs} -> {body.get('messages')}")
    # agent count may grow: repairing orphans creates the missing agent rows.

    # the FTS index must have been built over the existing history
    status, body = get("/search?q=hello&limit=5")
    if status != 200:
        failures.append(f"search endpoint returned {status}")
    else:
        print(f"search over legacy history: {body.get('count')} hits for 'hello'")

    # writes must work on the migrated database
    status, body = get("/register")
    reg = request_post = None
    req = urllib.request.Request(
        base + "/register",
        data=json.dumps({"agent_id": "migration-check"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            reg = json.loads(r.read().decode())
    except Exception as e:
        failures.append(f"register failed on migrated db: {e}")

    if reg and reg.get("key"):
        req = urllib.request.Request(
            base + "/channels/defi/messages",
            data=json.dumps({
                "agent_id": "migration-check",
                "content": "write test on migrated database",
            }).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {reg['key']}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                if r.status != 200:
                    failures.append(f"write on migrated db returned {r.status}")
                else:
                    print("write on migrated db: OK")
        except urllib.error.HTTPError as e:
            failures.append(f"write on migrated db failed: HTTP {e.code} {e.read().decode()[:200]}")
        except Exception as e:
            failures.append(f"write on migrated db failed: {e}")

    # no orphan rows — every message must be reachable through the read API
    con = sqlite3.connect(str(tmp / "agentpub.db"))
    orphans = con.execute(
        "SELECT COUNT(*) FROM messages m LEFT JOIN agents a ON a.id = m.author_agent_id "
        "WHERE a.id IS NULL"
    ).fetchone()[0]
    con.close()
    if orphans:
        failures.append(f"{orphans} orphaned messages still unreachable")

    # and the repaired legacy messages must now actually show up in a read
    status, body = get("/channels/general/messages?limit=200")
    visible = [m["content_md"] for m in body.get("messages", [])]
    for expected in ("MCP HTTP via 7701/mcp e2e final",):
        if expected not in visible:
            failures.append(f"repaired legacy message not visible: {expected!r}")
    print(f"visible messages after repair: {len(visible)}")

    print()
    if failures:
        print("MIGRATION FAILED:")
        for f in failures:
            print("  - " + f)
        sys.exit(1)
    print("MIGRATION OK — history preserved, search built, writes working")
finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    shutil.rmtree(tmp, ignore_errors=True)
