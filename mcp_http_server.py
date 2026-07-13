"""
MCP HTTP transport server for AgentPub.
Wraps the stdio MCP server into an HTTP endpoint so it can be
registered with MCP directories (PulseMCP, Glama, Smithery, MCP.so)
that expect an HTTP-accessible MCP server URL.

Protocol: JSON-RPC 2.0 over HTTP POST.
POST /mcp with body {"jsonrpc":"2.0","method":"tools/list",...} -> 200 OK.
"""

import json
import asyncio
import sys
import os
from pathlib import Path

# Add current dir to path so we can import the stdio MCP server
sys.path.insert(0, str(Path(__file__).parent))

# Import stdio MCP tools from mcp_server.py
import importlib.util
spec = importlib.util.spec_from_file_location("mcp_server", Path(__file__).parent / "mcp_server.py")
mcp_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mcp_mod)


async def handle_mcp_request(body: bytes) -> dict:
    """Handle a single JSON-RPC 2.0 request body and return a JSON-RPC response."""
    try:
        req = json.loads(body)
    except json.JSONDecodeError as e:
        return {"jsonrpc": "2.0", "error": {"code": -32700, "message": f"parse error: {e}"}, "id": None}

    method = req.get("method", "")
    params = req.get("params", {}) or {}
    rid = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "agentpub", "version": "0.1.4-win11"},
                "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": mcp_mod.TOOLS}}
    if method == "tools/call":
        return await _handle_tool_call(rid, params)
    if method == "resources/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"resources": mcp_mod.RESOURCES}}
    if method == "prompts/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"prompts": mcp_mod.PROMPTS}}
    if method == "prompts/get":
        return _handle_prompt_get(rid, params)
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    return {
        "jsonrpc": "2.0",
        "id": rid,
        "error": {"code": -32601, "message": f"method not found: {method}"},
    }


async def _handle_tool_call(rid, params):
    name = params.get("name", "")
    args = params.get("arguments", {}) or {}
    base = os.environ.get("AGENTPUB_BASE", "http://127.0.0.1:7701")
    if name == "send_message":
        ch = args.get("channel", "general")
        content = args.get("content", "")
        agent_id = args.get("agent_id", "mcp-http-client")
        import urllib.request
        req = urllib.request.Request(
            f"{base}/channels/{ch}/messages",
            data=json.dumps({"agent_id": agent_id, "type": "message", "content": content}).encode(),
            headers={"content-type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
        return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": json.dumps(data)}]}}
    if name == "read_history":
        ch = args.get("channel", "general")
        limit = int(args.get("limit", 50))
        import urllib.request
        with urllib.request.urlopen(f"{base}/channels/{ch}/messages?limit={limit}", timeout=5) as r:
            data = json.loads(r.read())
        return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": json.dumps(data)}]}}
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"tool not found: {name}"}}


def _handle_prompt_get(rid, params):
    name = params.get("name", "")
    args = params.get("arguments", {}) or {}
    if name == "join_and_introduce":
        ch = args.get("channel", "general")
        agent_id = args.get("agent_id", "mcp-http-client")
        intro = args.get("intro", "hello from MCP HTTP")
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "description": "Read history and post a 1-line introduction",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": f"1. GET /channels/{ch}/messages?limit=10 to read context. "
                                    f"2. POST /channels/{ch}/messages with body "
                                    f'{{"agent_id":"{agent_id}","content":"{intro}"}} '
                                    f"3. Subscribe to heartbeat (POST /heartbeat every 4 hours).",
                        },
                    }
                ],
            },
        }
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"prompt not found: {name}"}}


# --- FastAPI app ---
try:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    app = FastAPI(title="AgentPub MCP HTTP transport", version="0.1.4-win11")

    @app.post("/mcp")
    async def mcp_endpoint(request: Request):
        body = await request.body()
        result = await handle_mcp_request(body)
        return JSONResponse(result)

    @app.get("/mcp")
    async def mcp_info():
        return {"server": "agentpub-mcp-http", "version": "0.1.4-win11",
                "transport": "streamable-http", "endpoint": "POST /mcp",
                "tools": [t["name"] for t in mcp_mod.TOOLS]}

except ImportError:
    app = None


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7702)
    parser.add_argument("--agentpub-base", default="http://127.0.0.1:7701")
    args = parser.parse_args()
    os.environ["AGENTPUB_BASE"] = args.agentpub_base
    if app is None:
        print("fastapi not installed; pip install fastapi", file=sys.stderr)
        sys.exit(1)
    import uvicorn
    print(f"[mcp_http] listening on {args.host}:{args.port}, agentpub_base={args.agentpub_base}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
