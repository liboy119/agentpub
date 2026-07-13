#!/usr/bin/env python3
"""AgentPub /api/crawl — KAI 7/13+ use crawl4ai to fetch+structure any URL.

Returns clean markdown + metadata that AgentPub orchestrator uses for:
  - mcp.so / glama / GitHub repo page auto-discovery
  - doc reading for "world cup" / "A 股" search results
  - any LLM task that needs structured web input

Original. KAI runs as the only browser on this machine for AgentPub.
"""
import asyncio
import json
import os
import sys
from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/api/crawl")
async def api_crawl(
    url: str = Query(..., description="Target URL to crawl"),
    max_chars: int = Query(50000, description="Truncate markdown at this many chars"),
    timeout_s: int = Query(20, description="Page load timeout in seconds"),
):
    """Fetch a URL, render JS, return markdown.

    Returns:
      {
        "url": ...,
        "title": ...,
        "markdown": ...,
        "metadata": {title, description, keywords},
        "truncated_at": N_or_null,
        "success": true,
      }
    """
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        from crawl4ai.cache_context import CacheMode
    except ImportError as e:
        return JSONResponse(
            {"error": f"crawl4ai not installed: {e}", "success": False}, status_code=500
        )

    if not url or not url.startswith(("http://", "https://")):
        return JSONResponse({"error": "url must start with http(s)://", "success": False}, status_code=400)

    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                page_timeout=timeout_s * 1000,
            )
            result = await crawler.arun(url=url, config=config)

        # CrawlResultContainer — 拿 inner _results[0]
        if hasattr(result, "_results") and result._results:
            inner = result._results[0]
            url_resp = inner.url
            md = inner.markdown or ""
            err = inner.error_message
            meta = getattr(inner, "metadata", None) or {}
        else:
            url_resp = getattr(result, "url", url)
            md = getattr(result, "markdown", "") or ""
            err = None
            meta = getattr(result, "metadata", None) or {}

        truncated = False
        if len(md) > max_chars:
            md = md[:max_chars] + "\n\n[... truncated, original length {0} chars]".format(len(md))
            truncated = True

        return {
            "url": url_resp,
            "title": meta.get("title") or "",
            "markdown": md,
            "metadata": meta,
            "truncated": truncated,
            "truncated_at_chars": max_chars,
            "success": not bool(err),
            "error": err or None,
        }
    except Exception as e:
        import traceback
        return JSONResponse(
            {
                "error": f"crawl exception: {str(e)[:200]}",
                "trace": traceback.format_exc()[:500],
                "url": url,
                "success": False,
            },
            status_code=500,
        )
