#!/usr/bin/env python3
"""Add GitHub topics using BASIC AUTH format (PAT fix)."""
import subprocess, json

with open('/tmp/.gh_token') as f:
    token = f.read().strip()

auth_user = "x-access-token"
auth_pass = token

topics = [
    "mcp-server",
    "agent-network",
    "ai-agents",
    "agent-chat",
    "websocket",
    "silicon-internet",
    "agent-discovery",
    "a2a",
    "model-context-protocol",
    "autonomous-agents",
    "agent-protocol",
    "multi-agent",
    "llm-agents",
    "agent-sdk",
    "python",
]

print(f"Setting {len(topics)} topics on liboy119/agentpub")
r = subprocess.run([
    "curl", "-s", "-X", "PUT",
    "-u", f"{auth_user}:{auth_pass}",
    "-H", "Accept: application/vnd.github+json",
    "-H", "X-GitHub-Api-Version: 2022-11-28",
    "-H", "Content-Type: application/json",
    "-d", json.dumps({"names": topics}),
    "https://api.github.com/repos/liboy119/agentpub/topics"
], capture_output=True, text=True, timeout=20)

print(f"stdout: {r.stdout[:800]}")
if r.stderr:
    print(f"stderr: {r.stderr[:200]}")

try:
    d = json.loads(r.stdout)
    if "names" in d:
        print(f"\n=== SUCCESS ===")
        print(f"  Set {len(d['names'])} topics: {d['names']}")
    else:
        print(f"\n=== FAILED ===")
        print(json.dumps(d, indent=2)[:800])
except Exception as e:
    print(f"Parse error: {e}")