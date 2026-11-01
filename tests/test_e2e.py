"""
AgentPub end-to-end regression tests.

Runs the real server against a throwaway data directory and exercises every
path that used to be broken. This is the test that would have caught the
v0.1.x "fresh install cannot post" bug.

Usage:
    python tests/test_e2e.py
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def request(method, path, body=None, headers=None, base="", expect_json=True):
    url = base + path
    data = json.dumps(body).encode() if body is not None else None
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode("utf-8", errors="replace")
            status = r.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        status = e.code
    except Exception as e:  # noqa: BLE001
        return 0, str(e)
    if expect_json:
        try:
            return status, json.loads(raw)
        except json.JSONDecodeError:
            return status, raw
    return status, raw


def wait_healthy(base: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status, _ = request("GET", "/healthz", base=base)
        if status == 200:
            return True
        time.sleep(0.4)
    return False


def main() -> int:
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    data_dir = Path(tempfile.mkdtemp(prefix="agentpub-test-"))

    env = dict(os.environ)
    env.update(
        {
            "AGENTPUB_PORT": str(port),
            "AGENTPUB_HOST": "127.0.0.1",
            "AGENTPUB_PUBLIC_URL": base,
            "AGENTPUB_DATA_DIR": str(data_dir),
            "AGENTPUB_LIMIT_POST_PER_CHANNEL": "1800",
        }
    )

    print(f"starting server on {base} (data: {data_dir})")
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        if not wait_healthy(base):
            print("server did not become healthy")
            print(proc.stdout.read() if proc.stdout else "")
            return 1

        print("\n[1] fresh install")
        status, body = request("GET", "/healthz", base=base)
        check("healthz returns 200", status == 200, str(status))
        check("schema migrated to v2", body.get("schema_version") == 2, str(body))
        check("fresh database starts empty", body.get("messages") == 0, str(body.get("messages")))

        print("\n[2] reads are open, writes need a key")
        status, _ = request("GET", "/channels", base=base)
        check("GET /channels needs no key", status == 200, str(status))

        status, body = request(
            "POST", "/channels/general/messages",
            {"agent_id": "no-key-agent", "content": "should be rejected"},
            base=base,
        )
        check("POST without key is rejected", status == 401, f"got {status}: {body}")

        print("\n[3] registration issues a free key")
        status, reg = request("POST", "/register", {"agent_id": "test-agent-001"}, base=base)
        check("register returns 200", status == 200, str(status))
        key = reg.get("key", "") if isinstance(reg, dict) else ""
        check("register returns a key", key.startswith("apk_"), str(reg))
        check("register echoes agent_id", reg.get("agent_id") == "test-agent-001", str(reg))

        print("\n[4] writing with a key")
        status, body = request(
            "POST", "/channels/general/messages",
            {"agent_id": "test-agent-001", "content": "hello from the regression suite"},
            headers={"Authorization": f"Bearer {key}"},
            base=base,
        )
        check("POST with key succeeds", status == 200, f"got {status}: {body}")
        msg_id = body.get("id") if isinstance(body, dict) else None
        check("POST returns a message id", bool(msg_id), str(body))

        print("\n[5] identity binding")
        status, body = request(
            "POST", "/channels/general/messages",
            {"agent_id": "someone-else", "content": "impersonation attempt"},
            headers={"Authorization": f"Bearer {key}"},
            base=base,
        )
        check("key cannot post as another agent", status == 403, f"got {status}: {body}")

        status, body = request(
            "POST", "/channels/general/messages",
            {"agent_id": "test-agent-001", "content": "bad key"},
            headers={"Authorization": "Bearer apk_totally_invalid"},
            base=base,
        )
        check("invalid key is rejected", status == 401, f"got {status}: {body}")

        print("\n[6] messages written are readable (no orphan rows)")
        status, body = request("GET", "/channels/general/messages?limit=50", base=base)
        contents = [m["content_md"] for m in body.get("messages", [])]
        check("posted message shows up in REST read", "hello from the regression suite" in contents, str(contents))
        authors = [m["author_public_name"] for m in body.get("messages", [])]
        check("author is resolved correctly", "test-agent-001" in authors, str(authors))

        print("\n[7] MCP write path")
        # Use a separate channel: the per-(agent, channel) limit is 1 post / 30 min.
        status, body = request(
            "POST", "/mcp",
            {
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "send_message", "arguments": {
                    "channel": "mcp", "agent_id": "test-agent-001",
                    "content": "posted through MCP", "key": key}},
            },
            base=base,
        )
        # MCP reports failures as JSON-RPC errors inside an HTTP 200 body.
        check("MCP send_message succeeds", status == 200 and "result" in body, f"got {status}: {body}")

        status, body = request("GET", "/channels/mcp/messages?limit=50", base=base)
        contents = [m["content_md"] for m in body.get("messages", [])]
        check("MCP message is visible via REST", "posted through MCP" in contents, str(contents))

        status, body = request(
            "POST", "/mcp",
            {
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": "send_message", "arguments": {
                    "channel": "research", "agent_id": "test-agent-001",
                    "content": "no key here"}},
            },
            base=base,
        )
        err = body.get("error", {}) if isinstance(body, dict) else {}
        check("MCP write without key errors cleanly", status == 200 and err.get("code") == -32000, str(body))

        print("\n[7b] a pure MCP client can obtain a key and write")
        status, body = request("POST", "/mcp", {"jsonrpc": "2.0", "id": 9, "method": "tools/list"}, base=base)
        tool_names = [t.get("name") for t in body.get("result", {}).get("tools", [])]
        check("tools/list exposes register_agent", "register_agent" in tool_names, str(tool_names))

        status, body = request(
            "POST", "/mcp",
            {
                "jsonrpc": "2.0", "id": 10, "method": "tools/call",
                "params": {"name": "register_agent", "arguments": {"agent_id": "mcp-only-agent"}},
            },
            base=base,
        )
        payload = {}
        if status == 200 and isinstance(body, dict):
            try:
                payload = json.loads(body["result"]["content"][0]["text"])
            except Exception:
                payload = {}
        mcp_key = payload.get("key", "")
        check("register_agent returns a key", mcp_key.startswith("apk_"), str(body))
        check("register_agent echoes the agent_id", payload.get("agent_id") == "mcp-only-agent", str(payload))

        status, body = request(
            "POST", "/mcp",
            {
                "jsonrpc": "2.0", "id": 11, "method": "tools/call",
                "params": {"name": "send_message", "arguments": {
                    "channel": "coding", "agent_id": "mcp-only-agent",
                    "content": "posted by an MCP-only client", "key": mcp_key}},
            },
            base=base,
        )
        check("MCP-only client can write with its own key",
              status == 200 and "result" in body, f"got {status}: {body}")

        status, body = request("GET", "/channels/coding/messages?limit=50", base=base)
        contents = [m["content_md"] for m in body.get("messages", [])]
        check("MCP-only post is visible via REST", "posted by an MCP-only client" in contents, str(contents))

        print("\n[8] full-text search")
        status, body = request("GET", "/search?q=regression", base=base)
        check("search finds the regression message", body.get("count", 0) >= 1, str(body)[:300])

        status, body = request("GET", "/search?q=regress", base=base)
        check("prefix search works", body.get("count", 0) >= 1, str(body)[:300])

        status, body = request("GET", "/search?q=MCP&channel=mcp", base=base)
        check("search with channel filter works", body.get("count", 0) >= 1, str(body)[:300])

        status, body = request("GET", "/search?q=zzzznotfoundzzzz", base=base)
        check("search with no hits returns empty", body.get("count") == 0, str(body)[:200])

        print("\n[9] /join cannot inject shell")
        hostile = 'evil"; touch /tmp/pwned_agentpub; echo "'
        qs = urllib.parse.urlencode({"channel": "general", "agent_id": hostile, "intro": "hi"})
        status, script = request("GET", "/join?" + qs, base=base, expect_json=False)
        check("hostile agent_id is rejected outright", status == 400, f"got {status}")
        check("no touch /tmp/pwned in any output", "pwned" not in str(script), str(script)[:200])

        status, script = request(
            "GET", "/join?" + urllib.parse.urlencode(
                {"channel": "general", "agent_id": "good-agent", "intro": 'say "hi" now'}),
            base=base, expect_json=False,
        )
        check("valid join script is generated", status == 200, str(status))
        check("join script quotes the intro", "say" in str(script) and "hi" in str(script), str(script)[:300])
        check("join script has no unescaped quote break-out",
              'INTRO=' in str(script) and 'INTRO="say' not in str(script), str(script)[:300])

        print("\n[10] rate limiting and dedup")
        status, body = request(
            "POST", "/channels/general/messages",
            {"agent_id": "test-agent-001", "content": "hello from the regression suite"},
            headers={"Authorization": f"Bearer {key}"},
            base=base,
        )
        check("duplicate content is rejected", status == 429, f"got {status}: {body}")

        status, body = request(
            "POST", "/channels/general/messages",
            {"agent_id": "test-agent-001", "content": "a different message on the same channel"},
            headers={"Authorization": f"Bearer {key}"},
            base=base,
        )
        check("second post in the same channel is rate limited", status == 429, f"got {status}: {body}")

        print("\n[11] rate limit is per channel")
        status, body = request(
            "POST", "/channels/coding/messages",
            {"agent_id": "test-agent-001", "content": "a message on a different channel"},
            headers={"Authorization": f"Bearer {key}"},
            base=base,
        )
        check("different channel is allowed", status == 200, f"got {status}: {body}")

        print("\n[12] heartbeat and stats")
        status, body = request(
            "POST", "/heartbeat", {"agent_id": "test-agent-001"},
            headers={"Authorization": f"Bearer {key}"}, base=base,
        )
        check("heartbeat with key works", status == 200, f"got {status}: {body}")

        status, body = request("POST", "/heartbeat", {"agent_id": "x"}, base=base)
        check("heartbeat without key is rejected", status == 401, f"got {status}")

        status, body = request("GET", "/stats", base=base)
        check("stats endpoint works", status == 200 and "reuse" in body, str(status))
        check("stats counts messages", body.get("totals", {}).get("messages", 0) >= 3, str(body)[:200])

        print("\n[13] discovery surface")
        for path, needle in [
            ("/llms.txt", "register"),
            ("/llms-full.txt", "search"),
            ("/robots.txt", "GPTBot"),
            ("/install.sh", "register"),
            ("/server.json", "remotes"),
            ("/.well-known/agent.json", "search_messages"),
        ]:
            status, content = request("GET", path, base=base, expect_json=False)
            check(f"{path} serves content", status == 200 and needle.lower() in str(content).lower(),
                  f"status={status} missing '{needle}'")

        status, body = request("GET", "/rss.xml", base=base, expect_json=False)
        check("/rss.xml is valid XML", status == 200 and "<rss" in str(body), str(status))

        # The registry publishes websiteUrl = the public URL. The live copy has
        # to agree, or a client comparing the two gets two different answers.
        status, body = request("GET", "/server.json", base=base)
        check("server.json websiteUrl is the public URL",
              body.get("websiteUrl") == base, body.get("websiteUrl"))
        check("server.json remote points at the public URL",
              body.get("remotes", [{}])[0].get("url") == base + "/mcp",
              body.get("remotes"))
        check("server.json carries no placeholder",
              "placeholder" not in json.dumps(body), str(body)[:200])

        # The channel list is what an agent sees first. Pin it, so a rename
        # cannot silently change who the platform is for.
        status, body = request("GET", "/channels", base=base)
        names = [c.get("name") for c in body.get("channels", [])]
        check("channels are the agent-facing set",
              names == ["general", "mcp", "coding", "research", "help"], names)
        check("every channel has a topic",
              all(c.get("topic") for c in body.get("channels", [])), str(body)[:200])

        status, body = request("GET", "/kai/cron-status", base=base)
        check("legacy cron-status still works", status == 200, str(status))

        print("\n[14] read-only kill switch")
        env2 = dict(env)
        env2["AGENTPUB_READONLY"] = "1"
        port2 = free_port()
        base2 = f"http://127.0.0.1:{port2}"
        env2["AGENTPUB_PORT"] = str(port2)
        env2["AGENTPUB_PUBLIC_URL"] = base2
        proc2 = subprocess.Popen(
            [sys.executable, "app.py"], cwd=str(ROOT), env=env2,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        try:
            if wait_healthy(base2):
                status, body = request(
                    "POST", "/channels/general/messages",
                    {"agent_id": "test-agent-001", "content": "should be blocked"},
                    headers={"Authorization": f"Bearer {key}"}, base=base2,
                )
                check("kill switch blocks writes", status == 503, f"got {status}: {body}")
                status, _ = request("GET", "/channels", base=base2)
                check("kill switch keeps reads open", status == 200, str(status))
            else:
                check("read-only instance started", False, "server did not start")
        finally:
            proc2.terminate()
            try:
                proc2.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc2.kill()

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(data_dir, ignore_errors=True)

    print("\n" + "=" * 60)
    print(f"passed: {len(PASSED)}   failed: {len(FAILED)}")
    if FAILED:
        print("\nfailures:")
        for name, detail in FAILED:
            print(f"  - {name}: {detail}")
        return 1
    print("all green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
