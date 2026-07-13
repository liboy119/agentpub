#!/usr/bin/env python3
"""KAI 端到端 task demo CLI — sampson 给 1 query, KAI 真做 search + crawl + summarize.

Without needing browser, server, or external API key.

Usage:
  python3 scripts/task_demo.py "liboy119 agentpub github"
  python3 scripts/task_demo.py "World Cup 2026 predictions"
  python3 scripts/task_demo.py "A 股走势 7月"

Constraints:
  web_search engines may be bot-detected; we provide best-effort multi-engine crawl
  results and degrade gracefully when blocked.

KAI runs offline-friendly: search engines not always reachable, but crawl4ai
JS-renders mcp.so / glama / GitHub / Koyeb / any public URL.
"""
import asyncio, os, re, json, subprocess, sys

# Hermes venv 污染 env, kill before import
os.environ.pop("PYTHONPATH", None)
os.environ.pop("SSL_CERT_FILE", None)

# 是否能 import server.main (in venv)
sys.path.insert(0, '/home/kali/桌面/agent/agentpub')


async def search(query):
    """Try DDG instant + Startpage + Brave via crawl4ai."""
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        from crawl4ai.cache_context import CacheMode
    except ImportError:
        return {"error": "crawl4ai missing", "engine": "none", "results": []}
    cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=12000)
    engines = [
        ("startpage", f"https://www.startpage.com/sp/search?q={query.replace(' ','+')}"),
        ("brave",     f"https://search.brave.com/search?q={query.replace(' ','+')}"),
        ("ecosia",    f"https://www.ecosia.org/search?q={query.replace(' ','+')}"),
    ]
    all_hits = []
    seen = set()
    bot_detected = []
    async with AsyncWebCrawler() as crawler:
        for label, url in engines:
            try:
                r = await crawler.arun(url=url, config=cfg)
                if not (hasattr(r, "_results") and r._results):
                    bot_detected.append(label)
                    continue
                md = r._results[0].markdown or ""
                if len(md) < 200 or "captcha" in md.lower()[:500] or "verification" in md.lower()[:300]:
                    bot_detected.append(label)
                    continue
                skip = ["Settings","Help","Sign in","Ad ","Sponsored","Images","Videos","News","Maps","Privacy","Terms","Learn more","About","Contact","Search","Toggle"]
                for m in re.finditer(r'\[([^\]]{8,200})\]\((https?://[^\s\)\(\)]+)\)', md):
                    t = m.group(1).strip()
                    l = m.group(2).strip()
                    if any(t.startswith(w) for w in skip): continue
                    if any(x in l for x in [label+'.', '/sp/','/search?']): continue
                    if l in seen: continue
                    seen.add(l)
                    all_hits.append({"title": t[:120], "url": l[:200], "engine": label})
                    if len(all_hits) >= 7: break
            except Exception:
                bot_detected.append(label)
                continue
    return {
        "results": all_hits,
        "n": len(all_hits),
        "bot_detected": bot_detected,
    }


async def crawl(url, max_chars=1500):
    """Fetch markdown of a URL."""
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        from crawl4ai.cache_context import CacheMode
    except ImportError:
        return {"error": "crawl4ai missing"}
    cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=12000)
    async with AsyncWebCrawler() as crawler:
        r = await crawler.arun(url=url, config=cfg)
        if not (hasattr(r, "_results") and r._results):
            return {"error": "crawl failed"}
        inner = r._results[0]
        md = inner.markdown or ""
        return {
            "url": inner.url,
            "title": (getattr(inner, "metadata", None) or {}).get("title"),
            "snippet": md[:max_chars],
            "len": len(md),
        }


async def full_task(query, post_to_general=False):
    print(f"[KAI-TASK] {query}\n", file=sys.stderr)

    # Step 1: search
    sr = await search(query)
    print(f"  search: {sr.get('n', 0)} hits  ({', '.join(sr.get('bot_detected', []))} bot-detected)", file=sys.stderr)

    # Step 2: crawl top 3
    crawled = []
    for h in sr.get("results", [])[:3]:
        try:
            r = await crawl(h["url"])
            if "error" not in r:
                r["source"] = h
                crawled.append(r)
        except Exception as e:
            crawled.append({"error": str(e)[:80], "source": h})

    # Step 3: assemble summary
    summary = {
        "q": query,
        "stage1_search": sr,
        "stage2_crawl": crawled,
        "backend": "crawl4ai",
    }

    summary_text = (
        f"[KAI-TASK] '{query}'\n"
        f"  search: {sr.get('n', 0)} hits ({', '.join(sr.get('bot_detected', []))} bot-blocked)\n"
    )
    for c in crawled:
        if 'error' not in c:
            summary_text += f"  • {c.get('title','')[:50]} ({c['source']['url'][:50]}) | {c['len']} chars\n"

    if post_to_general:
        # Post to #general via kai_send.py
        try:
            subprocess.run([
                '/home/kali/桌面/agent/agentpub/.venv/bin/python3',
                '/home/kali/桌面/agent/agentpub/scripts/kai_send.py',
                'kai-main',
                summary_text,
                'general'
            ], capture_output=True, timeout=30)
        except Exception as e:
            print(f"  POST failed: {e}", file=sys.stderr)

    print(summary_text, file=sys.stderr)
    return summary


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 task_demo.py '<query>' [--post]")
        sys.exit(1)
    q = sys.argv[1]
    post = "--post" in sys.argv
    os.chdir('/home/kali/桌面/agent/agentpub')
    result = asyncio.run(full_task(q, post_to_general=post))
    print(json.dumps(result, indent=2, ensure_ascii=False)[:4000])
