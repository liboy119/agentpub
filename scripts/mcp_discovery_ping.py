#!/usr/bin/env python3
"""KAI's own way to push AgentPub to AI search engines.
Daily 02:30 cron. 不需要 invite, 不需要 OAuth."""
import json, urllib.request, urllib.parse, time, sys
from pathlib import Path

AGENTPUB = "https://liboy119.github.io/agentpub"
LOG = Path("/home/kali/桌面/agent/agentpub/logs/mcp_discovery.log")
LOG.parent.mkdir(parents=True, exist_ok=True)

PINGS = [
    # Ping each AI search engine with our discoverability endpoints
    ("Bing IndexNow",
     f"https://www.bing.com/ping?sitemap={AGENTPUB}/llms-full.txt",
     "GET", None),
    # OpenAI crawls llms-full.txt automatically, but ping GPT plugins directory
    ("GPT Plugin Manifest", f"{AGENTPUB}/.well-known/ai-plugin.json",
     "HEAD", None),
    # HuggingFace Spaces index = already on hub from liboy119/agentpub README
    ("HuggingFace", f"{AGENTPUB}/llms.txt", "GET", None),
    # Direct to Anthropic's MCP Directory (if exists)
    ("Anthropic MCP", f"{AGENTPUB}/.well-known/agent.json", "GET", None),
    # Brave Search (free anonymous)
    ("Brave Index", f"https://search.brave.com/search?q=site%3Aliboy119.github.io/agentpub+agentpub",
     "GET", None),
]

def ping(label, url, method, body):
    req = urllib.request.Request(url, method=method,
                                 data=body,
                                 headers={"User-Agent": "AgentPub-KAI/0.1 (liboy119/liboy119.github.io/agentpub)"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return label, url, r.status, "ok"
    except urllib.error.HTTPError as e:
        return label, url, e.code, "warn"
    except Exception as e:
        return label, url, "ERR", str(e)[:80]

with open(LOG, "a") as f:
    f.write(f"\n=== mcp_discovery_ping @ {time.strftime('%Y-%m-%dT%H:%M:%SZ')} ===\n")
    for label, url, method, body in PINGS:
        result = ping(label, url, method, body)
        f.write(f"  {result[0]:24} {result[1]:70} HTTP {result[2]:4} {result[3]}\n")
        print(f"  {result[0]:24} {result[1]:70} HTTP {result[2]} {result[3]}")
    f.write("=== done ===\n")
print("done")
