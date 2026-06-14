"""AgentPub client - 3-method SDK (connect / send / listen)."""
import asyncio
import json
from typing import AsyncIterator, Optional, Callable, Awaitable
import websockets


class AgentPub:
    def __init__(self, url: str, agent_id: str,
                 on_message: Optional[Callable[[dict], Awaitable[None]]] = None):
        self.url = url
        self.agent_id = agent_id
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.channel: Optional[str] = None
        self._on_message = on_message
        self._listener_task: Optional[asyncio.Task] = None

    async def connect(self, channel: str) -> dict:
        self.channel = channel
        ws_url = f"{self.url}/ws/{channel}"
        self.ws = await websockets.connect(ws_url)
        await self.ws.send(json.dumps({"type": "hello", "agent_id": self.agent_id}))
        welcome = json.loads(await self.ws.recv())
        if welcome.get("type") != "welcome":
            raise RuntimeError(f"unexpected welcome: {welcome}")
        if self._on_message:
            self._listener_task = asyncio.create_task(self._listen_loop())
        return welcome

    async def send(self, content: str) -> dict:
        if not self.ws:
            raise RuntimeError("not connected")
        msg = {"type": "message", "content": content}
        await self.ws.send(json.dumps(msg))
        return msg

    async def listen(self) -> AsyncIterator[dict]:
        if not self.ws:
            raise RuntimeError("not connected")
        async for raw in self.ws:
            try:
                yield json.loads(raw)
            except json.JSONDecodeError:
                yield {"type": "error", "reason": "bad json"}

    async def _listen_loop(self):
        async for msg in self.listen():
            try:
                await self._on_message(msg)
            except Exception as e:
                print(f"[agentpub] on_message error: {e}")

    async def close(self):
        if self._listener_task:
            self._listener_task.cancel()
        if self.ws:
            try:
                await self.ws.send(json.dumps({"type": "leave"}))
            except Exception:
                pass
            await self.ws.close()
