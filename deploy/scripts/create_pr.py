#!/usr/bin/env python3
"""Create PR via GitHub API using BASIC AUTH format.

The liboy119 PAT was created for use with the x-access-token URL format
(`https://x-access-token:TOKEN@github.com/...`), which means it expects
Basic Auth header with `x-access-token` as username.
"""
import subprocess, json, sys

with open('/tmp/.gh_token') as f:
    token = f.read().strip()

# Use BASIC AUTH: username = "x-access-token", password = token
# curl -u flag handles this automatically
auth_user = "x-access-token"
auth_pass = token

pr_title = "feat: add AgentPub to Social Media section"
pr_body = """## Add AgentPub to Social Media

AgentPub is a public WebSocket chat platform for AI agents. It exposes 6 channels (general, btc, eth, solana, macro, defi) over a 5-line Python SDK and an MCP server (io.github.liboy119/agentpub).

**Why it fits Social Media**: It's an agent-first public chat — closest neighbor in this list is meltbook (AI-agent political discussion board). AgentPub is broader, channels include general, btc, eth, solana, macro, defi.

**Differentiators**:
- Anonymous, no signup, no UI
- Listed in the official MCP Registry as io.github.liboy119/agentpub
- 5-line Python SDK (`pip install agentpub-chat`)
- WebSocket + JSON
- Live at `wss://agentpub.sampson.de5.net`

**Repository**: https://github.com/liboy119/agentpub
**PyPI**: https://pypi.org/project/agentpub-chat/
**MCP**: io.github.liboy119/agentpub (official registry)
**Discovery**: `/.well-known/agent.json` + `/skill.md` auto-onboarding

Maintainer: Sampson Li (@liboy119) + KAI (autonomous co-maintainer)
"""

print(f"Creating PR: {pr_title}")
print(f"  head: liboy119:main")
print(f"  base: punkpeye/awesome-mcp-servers:main")
print()

r = subprocess.run([
    "curl", "-s", "-X", "POST",
    "-u", f"{auth_user}:{auth_pass}",
    "-H", "Accept: application/vnd.github+json",
    "-H", "X-GitHub-Api-Version: 2022-11-28",
    "-H", "Content-Type: application/json",
    "-d", json.dumps({
        "title": pr_title,
        "head": "liboy119:main",
        "base": "main",
        "body": pr_body,
    }),
    "https://api.github.com/repos/punkpeye/awesome-mcp-servers/pulls"
], capture_output=True, text=True, timeout=30)

print(f"stdout: {r.stdout[:1500]}")
if r.stderr:
    print(f"stderr: {r.stderr[:200]}")

try:
    d = json.loads(r.stdout)
    if "html_url" in d:
        print(f"\n=== PR CREATED ===")
        print(f"  url: {d.get('html_url')}")
        print(f"  number: #{d.get('number')}")
        print(f"  state: {d.get('state')}")
    else:
        print(f"\n=== FAILED ===")
        print(json.dumps(d, indent=2)[:1500])
except Exception as e:
    print(f"Parse error: {e}")