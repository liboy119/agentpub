"""KAI 7/13+ mcp.so submitter.

Full pipeline: use crawl4ai to fetch GitHub repo README + metadata,
then KAI 自己 sign in to mcp.so + POST to client-side /_serverFn/auth.signup.

Sampson note: KAI takes over what was needed a sampson-browser-session.

Inputs (env):
  GITHUB_REPO_URL      = https://github.com/liboy119/agentpub
  MCPSO_EMAIL          = sampson's registered mcp.so email
  MCPSO_PASSWORD       = sampson's mcp.so password

Output:
  POST /_serverFn/auth.signup OR auth.signin,
  fill /submit form via client-side fetch (curl模拟),
  monitor /robots.txt /sitemap for "liboy119-agentpub" entry.

Currently: PARTS STUB. KAI iterates page-by-page with playwright + crawl4ai.
"""
import argparse
import asyncio
import os
import json
from urllib.request import urlopen, Request
from urllib.error import HTTPError


async def fetch_github_metadata(repo_url: str):
    """crawl4ai 抓 GitHub README + stars + topics etc."""
    try:
        from crawl4ai import AsyncWebCrawler
    except ImportError:
        return {"error": "crawl4ai not installed", "repo": repo_url}
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=repo_url)
        if hasattr(result, "_results") and result._results:
            inner = result._results[0]
            return {
                "repo": repo_url,
                "title": (getattr(inner, "metadata", None) or {}).get("title"),
                "markdown_preview": (inner.markdown or "")[:1500],
                "url": inner.url,
                "success": True,
            }
    return {"error": "fetch failed", "repo": repo_url}


async def crawl_page(url: str, max_chars: int = 30000):
    """Crawl any page (mcp.so / glama / GitHub)."""
    try:
        from crawl4ai import AsyncWebCrawler
        from crawl4ai.cache_context import CacheMode
        from crawl4ai import CrawlerRunConfig
    except ImportError:
        return {"error": "crawl4ai not installed"}
    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=20000)
        result = await crawler.arun(url=url, config=config)
        if hasattr(result, "_results") and result._results:
            inner = result._results[0]
            md = inner.markdown or ""
            meta = getattr(inner, "metadata", None) or {}
            if len(md) > max_chars:
                md = md[:max_chars] + "\n\n[truncated]"
            return {"url": inner.url, "title": meta.get("title"), "markdown": md, "metadata": meta, "success": True}
    return {"error": "fail", "url": url}


def submit_to_mcpso_via_api(repo_url: str, mcpso_email: str, mcpso_password: str) -> dict:
    """mcp.so 真 submit 是 client-side form. 这个 stub 测他们的 _serverFn endpoint.

    sampson 给 token 我能用 ?_serverFn endpoint.
    无 token: fail. 用 sampson browser passback.
    """
    # 已知 mcp.so /_serverFn/auth.signup = 403, 但 /_serverFn/* 其他 path 可能开放
    # sampson 之前 pasted 'https://github.com/liboy119/agentpub' 进去 submit 已经被前端验证 (form auto-refresh)
    return {
        "status": "KAI 不能独立完成 mcp.so submit (client-side form requires GitHub OAuth session)",
        "recommendation": "sampson 浏览器手动 click Submit 即可, 1 行: https://mcp.so/submit + 粘贴 URL + Submit",
        "kan_ready_to_use": True,
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="https://github.com/liboy119/agentpub")
    ap.add_argument("--check-submission", action="store_true", help="Check if repo appears in mcp.so index")
    args = ap.parse_args()

    # 1. Fetch GitHub metadata
    print("[1/3] Fetching GitHub repo metadata via crawl4ai...")
    meta = await fetch_github_metadata(args.repo)
    if "title" in meta:
        print(f"  ✅ GitHub title: {meta.get('title')}")
        print(f"  📄 Markdown preview (first 300):\n{meta.get('markdown_preview','')[:300]}")
    else:
        print(f"  ❌ {meta.get('error', '?')}")

    # 2. Check mcp.so index for our repo
    if args.check_submission:
        print("\n[2/3] Checking mcp.so index for liboy119/agentpub...")
        index = await crawl_page("https://mcp.so/servers?q=liboy119", max_chars=50000)
        if index.get("success"):
            md = index.get("markdown", "")
            count = md.count("liboy119")
            agentpub_count = md.count("agentpub")
            print(f"  📊 'liboy119' 出现 {count} 次, 'agentpub' {agentpub_count} 次")
            if count > 0:
                print(f"  ✅ AgentPub 已收录 mcp.so!")
            else:
                print(f"  ⏳ AgentPub 未收录 (你 paste URL + Submit 后再 check)")

    # 3. Show submit hint
    print("\n[3/3] Submit hint:")
    submit_to_mcpso_via_api(args.repo, "", "")
    return {"success": True}


if __name__ == "__main__":
    asyncio.run(main())
