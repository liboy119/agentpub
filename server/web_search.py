#!/usr/bin/env python3
"""AgentPub /api/tools/web_search v2 — KAI 7/13+ use crawl4ai for real search.

Multi-engine fallback: startpage (privacy-friendly, returns real results) > brave > duckduckgo.

DDG bot-detects heavily; HTML scraping returns 0 results. crawl4ai JS-renders
real search pages so we get actual <a href="..."> title text + url pairs.
"""
import asyncio
import os
import re
import sys

# CRITICAL: Hermes venv contaminates PYTHONPATH, kill it before importing
os.environ.pop("PYTHONPATH", None)
os.environ.pop("SSL_CERT_FILE", None)

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter()


async def _crawl_search_results(query: str, max_results: int = 5):
    """crawl Startpage + Brave + DDG, dedupe by domain, return top N."""
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        from crawl4ai.cache_context import CacheMode
    except ImportError as e:
        return {"error": f"crawl4ai missing: {e}", "results": [], "count": 0}

    cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=12000)
    engines = [
        ("startpage", f"https://www.startpage.com/sp/search?q={query}"),
        ("brave",     f"https://search.brave.com/search?q={query}"),
        ("ddg_html",  f"https://html.duckduckgo.com/html/?q={query}"),
    ]

    seen_urls = set()
    results = []
    engines_actually_returned = []

    async with AsyncWebCrawler() as crawler:
        for label, url in engines:
            try:
                r = await crawler.arun(url=url, config=cfg)
                if not (hasattr(r, "_results") and r._results):
                    continue
                md = r._results[0].markdown or ""
                if len(md) < 200:
                    continue  # bot-detected page, skip
                # 抽 [Title](url) 链接, 过滤掉自链
                page_hits = 0
                for m in re.finditer(r'\[([^\]]{2,150})\]\((https?://[^\s\)\(\)]+)\)', md):
                    title = m.group(1).strip()
                    link = m.group(2).strip()
                    # skip engine's own links
                    if any(x in link.lower() for x in [
                        "startpage.", "brave.com/search", "duckduckgo.", "html.duckduckgo",
                        "/settings", "/help", "/about",
                    ]):
                        continue
                    if any(x in title for x in [
                        "DuckDuckGo", "Brave", "Startpage", "Ad ", "Sponsored",
                        "Settings", "Help", "About", "Privacy",
                    ]):
                        continue
                    # skip bare text
                    if len(title) < 5 or not any(c.isalnum() for c in title):
                        continue
                    # dedupe
                    if link in seen_urls:
                        continue
                    seen_urls.add(link)
                    results.append({
                        "url": link[:250],
                        "title": title[:150],
                        "engine": label,
                    })
                    page_hits += 1
                    if page_hits >= max_results:
                        break
                if page_hits > 0:
                    engines_actually_returned.append(label)
                if len(results) >= max_results * 2:
                    break
            except Exception as e:
                # engine errored, continue
                continue

    return {
        "results": results[:max_results],
        "count": len(results[:max_results]),
        "engines_queried": [e for e, _ in engines],
        "engines_succeeded": engines_actually_returned,
    }


@router.get("/api/tools/web_search")
async def api_tools_web_search(
    q: str = Query(..., max_length=500, description="search query"),
    max_results: int = Query(5, le=10),
):
    """AgentPub built-in web search v2 — KAI 7/13+ uses crawl4ai to JS-render Startpage/Brave/DDG.

    Returns:
        {
            "q": "...",
            "results": [{url, title, engine}, ...],
            "count": N,
            "engines_queried": ["startpage","brave","ddg_html"],
            "engines_succeeded": ["startpage", ...],
            "backend": "crawl4ai_multi",
        }
    """
    if not q or len(q) > 500:
        return JSONResponse({"error": "q required (max 500 chars)"}, status_code=400)

    try:
        result = await _crawl_search_results(q, max_results)
        return {
            "q": q,
            **result,
            "backend": "crawl4ai_multi",
        }
    except Exception as e:
        import traceback
        return JSONResponse({
            "error": str(e)[:200],
            "trace": traceback.format_exc()[:500],
        }, status_code=500)
