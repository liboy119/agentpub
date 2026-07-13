#!/usr/bin/env python3
"""KAI auto-verify AgentPub 被 mcp.so / glama 收录.

每 10 分钟 cron 跑. 报告收录状态到 #general.
"""
import asyncio
import json
import os
import sys
from urllib.request import urlopen, Request

sys.path.insert(0, '/home/kali/桌面/agent/agentpub')


async def check_mcp_so():
    """crawl mcp.so 主页 + 搜 liboy119/agentpub."""
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        from crawl4ai.cache_context import CacheMode
    except ImportError:
        return {"error": "crawl4ai missing"}
    async with AsyncWebCrawler() as crawler:
        cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=15000)
        # 多个 query 路径
        results = []
        for url in [
            "https://mcp.so/servers?q=liboy119",
            "https://mcp.so/servers?q=agentpub",
            "https://mcp.so/servers?q=AgentPub",
        ]:
            r = await crawler.arun(url=url, config=cfg)
            if hasattr(r, "_results") and r._results:
                inner = r._results[0]
                md = (inner.markdown or "").lower()
                # 看 liboy119 / agentpub 出现次数
                cnt_lib = md.count("liboy119")
                cnt_agn = md.count("agentpub")
                # 找实际出现 liboy119 的链接 (server detail page)
                has_link = "/liboy119-agentpub" in md or "liboy119/agentpub" in md
                results.append({
                    "url": url,
                    "liboy119_mention": cnt_lib,
                    "agentpub_mention": cnt_agn,
                    "has_detail_link": has_link,
                })
        return results


async def check_glama():
    """crawl glama.ai 同样查."""
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        from crawl4ai.cache_context import CacheMode
    except ImportError:
        return {"error": "crawl4ai missing"}
    async with AsyncWebCrawler() as crawler:
        cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=15000)
        r = await crawler.arun(url="https://glama.ai/mcp/servers?q=liboy119", config=cfg)
        if hasattr(r, "_results") and r._results:
            inner = r._results[0]
            md = (inner.markdown or "").lower()
            return {
                "url": "glama.ai/mcp/servers?q=liboy119",
                "liboy119_mention": md.count("liboy119"),
                "agentpub_mention": md.count("agentpub"),
                "has_detail_link": "/liboy119-agentpub" in md or "liboy119/agentpub" in md,
            }


async def ping_llms_after_index():
    """如果 mcp.so 或 glama 已收录, mcp_discovery_ping 立刻跑 (push 5 AI 索引)."""
    import subprocess
    result = subprocess.run(
        ['python3', '/home/kali/桌面/agent/agentpub/scripts/mcp_discovery_ping.py'],
        capture_output=True, text=True, timeout=60
    )
    return {"ran": result.returncode == 0, "output_tail": result.stdout[-300:]}


async def post_to_general(summary_json: str):
    """post summary to #general channel."""
    import subprocess
    # 给 msg
    msg = f"[AUTO-VERIFY] {summary_json[:400]}"
    subprocess.run([
        '/home/kali/桌面/agent/agentpub/.venv/bin/python3',
        '/home/kali/桌面/agent/agentpub/scripts/kai_send.py',
        'kai-main',
        msg,
        'general'
    ], capture_output=True)


async def main():
    print("[verify] start", flush=True)
    results = {"ts": int(__import__('time').time())}

    mcp_results = await check_mcp_so()
    results["mcp_so"] = mcp_results
    print(f"[mcp.so] {mcp_results}", flush=True)

    glama_results = await check_glama()
    results["glama"] = glama_results
    print(f"[glama] {glama_results}", flush=True)

    # 检查收录
    mcp_indexed = any(r.get("has_detail_link") for r in mcp_results if isinstance(r, dict))
    glama_indexed = glama_results.get("has_detail_link") if isinstance(glama_results, dict) else False

    if mcp_indexed or glama_indexed:
        print("[verify] INDEXED — run mcp_discovery_ping", flush=True)
        await ping_llms_after_index()

    # post 到 #general
    summary = json.dumps({
        "mcp_indexed": mcp_indexed,
        "glama_indexed": glama_indexed,
        "mcp_so_hits": sum(r.get("liboy119_mention", 0) for r in mcp_results if isinstance(r, dict)),
        "glama_hits": glama_results.get("liboy119_mention", 0) if isinstance(glama_results, dict) else 0,
    })
    await post_to_general(summary)


if __name__ == "__main__":
    asyncio.run(main())
