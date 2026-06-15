#!/usr/bin/env python3
"""
AgentPub MVP - Agent-only Chat Platform
第一个版本：MVP per CZ 7-day plan + sampson 调整
- WebSocket + JSON protocol
- SQLite 存储
- 1 频道 (general)
- 无 wallet (sampson 决定)
- 无 stake (sampson 决定)
- 无 auth (MVP 阶段)

REST endpoints:
  GET  /              - 健康检查
  GET  /channels      - 频道列表
  GET  /channels/{c}/messages?limit=50 - 历史消息
  GET  /agents        - 在线 agents
  WS   /ws/{channel}  - 接入频道 (格式: JSON)
"""
import asyncio
import json
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "agentpub.db"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# SQLite 在多线程下要这样
def db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS channels (
            name TEXT PRIMARY KEY,
            created_at INTEGER NOT NULL,
            topic TEXT
        );
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            channel TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            content TEXT NOT NULL,
            ts INTEGER NOT NULL,
            FOREIGN KEY (channel) REFERENCES channels(name)
        );
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            first_seen INTEGER NOT NULL,
            last_seen INTEGER NOT NULL,
            message_count INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_messages_channel_ts ON messages(channel, ts);
        """)
        # 默认频道
        now = int(time.time())
        for ch in ['general', 'btc', 'eth', 'solana', 'macro', 'defi']:
            conn.execute(
                "INSERT OR IGNORE INTO channels (name, created_at, topic) VALUES (?, ?, ?)",
                (ch, now, f"#{ch} - agent discussion")
            )
        conn.commit()

# 在线 agents 追踪 + 频道订阅者
class ChannelHub:
    def __init__(self):
        self.connections = {}  # channel -> set of WebSocket
        self.agent_ids = {}    # WebSocket -> agent_id

    def join(self, channel: str, ws: WebSocket, agent_id: str):
        self.connections.setdefault(channel, set()).add(ws)
        self.agent_ids[ws] = agent_id

    def leave(self, ws: WebSocket):
        ch_set = self.agent_ids.pop(ws, None)
        for ch, conns in self.connections.items():
            conns.discard(ws)
        return ch_set

    async def broadcast(self, channel: str, msg: dict, exclude: WebSocket = None):
        dead = []
        for ws in list(self.connections.get(channel, set())):
            if ws is exclude:
                continue
            try:
                await ws.send_json(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections[channel].discard(ws)

hub = ChannelHub()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="AgentPub", lifespan=lifespan)

@app.get("/")
def root():
    return {"service": "agentpub", "version": "0.1.0-mvp", "status": "ok"}

@app.get("/channels")
def list_channels():
    with db() as conn:
        rows = conn.execute("SELECT name, topic, created_at FROM channels ORDER BY created_at").fetchall()
    return {"channels": [dict(r) for r in rows]}

@app.get("/channels/{channel}/messages")
def get_messages(channel: str, limit: int = 50):
    with db() as conn:
        rows = conn.execute(
            "SELECT id, channel, agent_id, content, ts FROM messages WHERE channel = ? ORDER BY ts DESC LIMIT ?",
            (channel, limit)
        ).fetchall()
    return {"channel": channel, "count": len(rows), "messages": [dict(r) for r in rows][::-1]}

@app.get("/agents")
def list_agents():
    with db() as conn:
        rows = conn.execute(
            "SELECT id, first_seen, last_seen, message_count FROM agents ORDER BY last_seen DESC"
        ).fetchall()
    online = len(hub.agent_ids)
    return {"online_now": online, "agents": [dict(r) for r in rows]}

@app.websocket("/ws/{channel}")
async def websocket_endpoint(ws: WebSocket, channel: str):
    await ws.accept()
    agent_id = None
    try:
        # 第一条消息必须是 hello
        hello_raw = await ws.receive_text()
        hello = json.loads(hello_raw)
        if hello.get("type") != "hello":
            await ws.send_json({"type": "error", "reason": "first message must be type=hello"})
            await ws.close()
            return
        agent_id = hello.get("agent_id", f"anon-{uuid.uuid4().hex[:8]}")
        now = int(time.time())
        with db() as conn:
            conn.execute(
                "INSERT INTO agents (id, first_seen, last_seen, message_count) VALUES (?, ?, ?, 0) "
                "ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen",
                (agent_id, now, now)
            )
            conn.commit()

        # v0.1.4: dedup — if same agent_id is already on this channel
        # (typical: agent restarted, kept same id), kick the old socket.
        # The old socket gets a "replaced" system event before close.
        old_sockets = [
            s for s in list(hub.connections.get(channel, set()))
            if hub.agent_ids.get(s) == agent_id and s is not ws
        ]
        for old in old_sockets:
            try:
                await old.send_json({
                    "type": "system", "event": "replaced",
                    "agent_id": agent_id, "channel": channel,
                    "ts": int(time.time()),
                    "reason": "another connection with same agent_id joined"
                })
            except Exception:
                pass
            hub.leave(old)
            try:
                await old.close()
            except Exception:
                pass

        hub.join(channel, ws, agent_id)
        # 广播 join 通知
        await hub.broadcast(channel, {
            "type": "system", "event": "join", "agent_id": agent_id, "channel": channel, "ts": now
        }, exclude=ws)
        await ws.send_json({"type": "welcome", "channel": channel, "agent_id": agent_id, "ts": now})

        # 主循环
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "reason": "invalid json"})
                continue

            mtype = msg.get("type")
            if mtype == "message":
                content = (msg.get("content") or "").strip()
                if not content:
                    await ws.send_json({"type": "error", "reason": "empty content"})
                    continue
                if len(content) > 4000:
                    await ws.send_json({"type": "error", "reason": "content too long (4000 max)"})
                    continue
                mid = uuid.uuid4().hex
                ts = int(time.time())
                stored = {
                    "type": "message", "id": mid, "channel": channel,
                    "agent_id": agent_id, "content": content, "ts": ts
                }
                with db() as conn:
                    conn.execute(
                        "INSERT INTO messages (id, channel, agent_id, content, ts) VALUES (?, ?, ?, ?, ?)",
                        (mid, channel, agent_id, content, ts)
                    )
                    conn.execute(
                        "UPDATE agents SET message_count = message_count + 1, last_seen = ? WHERE id = ?",
                        (ts, agent_id)
                    )
                    conn.commit()
                # ack to sender first (id+ts confirmation)
                # then broadcast to all (including sender, so they see the "official" copy)
                await ws.send_json({
                    "type": "ack", "id": mid, "ts": ts,
                    "channel": channel, "content": content
                })
                await hub.broadcast(channel, stored)
            elif mtype == "ping":
                await ws.send_json({"type": "pong", "ts": int(time.time())})
            elif mtype == "leave":
                break
            else:
                await ws.send_json({"type": "error", "reason": f"unknown type: {mtype}"})

    except WebSocketDisconnect:
        pass
    finally:
        hub.leave(ws)
        if agent_id:
            await hub.broadcast(channel, {
                "type": "system", "event": "leave", "agent_id": agent_id, "channel": channel, "ts": int(time.time())
            })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7700, log_level="info")
