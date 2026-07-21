"""KAI 7/14+ task orchestrator — sampson 浏览器提 task, 真路由 web_search + crawl.

POST /api/tasks  { type: "search", query: "world cup", depth: 3 }
GET /api/tasks/{id}  →  status + markdown summary + crawled urls
GET /api/tasks        → 列出 last 50 tasks
"""
import asyncio
import json
import os
import sys
import time
import uuid
from typing import Dict, List

# CRITICAL: Hermes venv contamination
os.environ.pop("PYTHONPATH", None)
os.environ.pop("SSL_CERT_FILE", None)

from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse

router = APIRouter()

# in-memory task store (sqlite is overkill for demo)
# Persisted to file so kai_reply_cron can also post results
TASKS_FILE = "/home/kali/桌面/agent/agentpub/data/tasks.json"
os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)

def _load_tasks() -> Dict:
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_tasks(t: Dict):
    with open(TASKS_FILE, "w") as f:
        json.dump(t, f, indent=2)


async def _run_search_and_crawl(query: str, depth: int = 2, max_chars: int = 4000) -> Dict:
    """真跑 pipeline: web_search v2 → crawl top hits → 综合 markdown."""
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        from crawl4ai.cache_context import CacheMode
        from urllib.parse import quote
        import re
    except Exception as e:
        return {"error": f"deps missing: {e}"}

    cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=12000)
    hits = []
    crawled = []

    async with AsyncWebCrawler() as crawler:
        # Stage 1: search via startpage (we showed it works)
        for engine, url in [
            ("startpage", f"https://www.startpage.com/sp/search?q={quote(query.replace(' ', '+'))}"),
            ("brave",     f"https://search.brave.com/search?q={quote(query.replace(' ', '+'))}"),
            ("ecosia",    f"https://www.ecosia.org/search?q={quote(query.replace(' ', '+'))}"),
        ]:
            try:
                r = await crawler.arun(url=url, config=cfg)
                if not (hasattr(r, "_results") and r._results):
                    continue
                md = r._results[0].markdown or ""
                if len(md) < 200 or "captcha" in md.lower()[:500] or "verification" in md.lower()[:300]:
                    continue
                skip = ["Settings","Help","Sign in","Ad ","Sponsored","Images","Videos","News","Maps","Privacy","Terms","Learn more","About","Contact","Search","Toggle"]
                for m in re.finditer(r'\[([^\]]{8,200})\]\((https?://[^\s\)\(\)]+)\)', md):
                    title = m.group(1).strip()
                    link = m.group(2).strip()
                    if any(title.startswith(w) for w in skip): continue
                    if any(x in link for x in [engine+'.', '/sp/', '/search?']): continue
                    if link in [h["url"] for h in hits]: continue
                    hits.append({"title": title[:120], "url": link[:200], "engine": engine})
                    if len(hits) >= max(depth * 2, 5): break
            except Exception:
                continue

        # Stage 2: crawl top N
        for h in hits[:depth]:
            try:
                r = await crawler.arun(url=h["url"], config=cfg)
                if not (hasattr(r, "_results") and r._results):
                    continue
                inner = r._results[0]
                md = inner.markdown or ""
                crawled.append({
                    "url": inner.url,
                    "title": (getattr(inner, "metadata", None) or {}).get("title") or h["title"],
                    "engine": h["engine"],
                    "len": len(md),
                    "snippet": md[:max_chars],
                })
            except Exception:
                continue

    # Stage 3: 综合 summary
    summary_lines = [f"# Search results for '{query}'", ""]
    summary_lines.append(f"**{len(hits)} hits** from Startpage/Brave/Ecosia")
    summary_lines.append(f"**{len(crawled)} crawled**\n")
    for c in crawled:
        summary_lines.append(f"## {c['title'][:80]} ({c['url'][:60]})")
        summary_lines.append(f"- engine: {c['engine']}")
        summary_lines.append(f"- content: {c['len']} chars")
        summary_lines.append(f"- snippet:\n```\n{c['snippet'][:300].strip()}\n```\n")

    return {
        "q": query,
        "n_hits": len(hits),
        "n_crawled": len(crawled),
        "hits": hits,
        "crawled": crawled,
        "summary_markdown": "\n".join(summary_lines),
        "backend": "crawl4ai",
    }


@router.get("/api/tasks")
async def list_tasks(limit: int = Query(50, le=200)):
    tasks = _load_tasks()
    items = [
        {"id": k, **v}
        for k, v in sorted(tasks.items(), key=lambda x: x[1].get("created", ""), reverse=True)[:limit]
    ]
    return {"count": len(items), "tasks": items}


@router.post("/api/tasks")
async def submit_task(request: Request):
    """Sampson 浏览器 POST form → 真 task pipeline."""
    try:
        body = await request.json()
    except Exception:
        # 如果是 form POST (不是 json), 试 form
        try:
            form = await request.form()
            body = dict(form)
        except Exception:
            return JSONResponse({"error": "expected json or form body"}, status_code=400)

    q = body.get("q") or body.get("query") or body.get("input")
    if not q or len(q) > 1000:
        return JSONResponse({"error": "q (or query) required, max 1000 chars"}, status_code=400)

    depth = int(body.get("depth", 2))
    task_id = uuid.uuid4().hex[:12]
    tasks = _load_tasks()
    tasks[task_id] = {
        "status": "running",
        "q": q,
        "depth": depth,
        "created": int(time.time()),
        "type": body.get("type", "search"),
    }
    _save_tasks(tasks)

    # 真跑 (同步, demo 4-8s)
    try:
        result = await _run_search_and_crawl(q, depth)
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result"] = result
        tasks[task_id]["completed"] = int(time.time())
    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(e)
        tasks[task_id]["completed"] = int(time.time())
    _save_tasks(tasks)

    return JSONResponse({
        "task_id": task_id,
        "status": tasks[task_id]["status"],
        "q": q,
        "result_preview": tasks[task_id].get("result", {}).get("summary_markdown", "")[:500] if tasks[task_id].get("result") else None,
        "full_result_url": f"/api/tasks/{task_id}",
    })


@router.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    tasks = _load_tasks()
    if task_id not in tasks:
        return JSONResponse({"error": f"task {task_id} not found"}, status_code=404)
    return tasks[task_id]


@router.get("/task_demo")
async def task_demo_page():
    """Sampson 浏览器友好的 HTML demo page.

    GET /task_demo → HTML form 让 sampson 输 query, 提 task, 看到结果.
    不需要 sampson 装 curl/python, sampson 用浏览器.
    """
    html = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>AgentPub Task Demo — sampson 浏览器试用</title>
  <style>
    body { font-family: -apple-system, sans-serif; max-width: 720px; margin: 2em auto; padding: 1em; }
    textarea { width: 100%; height: 80px; }
    button { padding: 8px 16px; background: #4a90e2; color: white; border: none; border-radius: 4px; cursor: pointer; }
    pre { background: #f4f4f4; padding: 12px; border-radius: 4px; overflow-x: auto; }
    .hit { background: #e6f7ff; padding: 6px 12px; margin: 4px 0; border-radius: 4px; }
  </style>
</head>
<body>
  <h1>AgentPub Task Demo</h1>
  <p>假装 sampson 你提 task (例: world cup 2026 predictions, A 股 7月, liboy119 agentpub)</p>
  <form id="f">
    <label>query:<br><textarea name="q" id="q" placeholder="world cup 2026 predictions">world cup 2026 predictions</textarea></label>
    <label>depth (1-5): <input name="depth" id="depth" type="number" value="2" min="1" max="5"></label>
    <br><button type="button" onclick="go()">跑任务</button>
  </form>
  <hr>
  <h2>结果</h2>
  <pre id="out">(running...)</pre>

  <script>
  async function go() {
    const q = document.getElementById('q').value;
    const depth = document.getElementById('depth').value;
    document.getElementById('out').innerText = '提交 task: ' + q + '...';
    const r = await fetch('/api/tasks', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({q: q, depth: parseInt(depth)})
    });
    const j = await r.json();
    document.getElementById('out').innerText = JSON.stringify(j, null, 2);
    if (j.task_id) {
      setTimeout(() => checkResult(j.task_id), 2000);
    }
  }
  async function checkResult(id) {
    const r = await fetch('/api/tasks/' + id);
    const j = await r.json();
    document.getElementById('out').innerText = JSON.stringify(j, null, 2);
  }
  </script>
</body>
</html>
"""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(html)
