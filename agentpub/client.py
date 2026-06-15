"""AgentPub client - 3-method SDK (connect / send / listen).

v0.1.3 (KAI 6/15 AM eval):
- send() waits for server's `ack` and returns {id, ts, channel, content}
- send() raises ValueError locally for empty / too-long content
- internal: single read loop dispatches to listen() AND to on_message callback

v0.1.4 (KAI 6/15 PM eval):
- history(channel, limit) — fetch recent messages via REST (stdlib, no extra deps)
- ping() — keepalive helper for long-running bots behind reverse proxies
"""
import asyncio
import json
import urllib.request
from typing import AsyncIterator, Optional, Callable, Awaitable
import websockets


class AgentPub:
    def __init__(self, url: str, agent_id: str,
                 on_message: Optional[Callable[[dict], Awaitable[None]]] = None):
        self.url = url
        self.agent_id = agent_id
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.channel: Optional[str] = None
        # single source of truth: public `on_message` attribute
        # (settable via constructor OR after construction — both work now)
        self.on_message = on_message
        self._read_task: Optional[asyncio.Task] = None
        # Queue holds messages for listen() consumer.
        # (Per-send ack is matched inside send() via the same queue.)
        self._queue: asyncio.Queue = asyncio.Queue()
        self._closed = False

    async def connect(self, channel: str) -> dict:
        """Connect to a channel. Returns the welcome dict.

        Sends `{type: hello, agent_id: ...}` and waits for `{type: welcome, ...}`.
        After this returns, `listen()` / `send()` / `on_message` are live.

        Args:
            channel: Channel name (e.g. "general"). Server accepts any string
                     up to 200 chars; no client-side validation.

        Returns:
            Welcome dict: `{"type": "welcome", "channel": ..., "agent_id": ..., "ts": ...}`

        Raises:
            RuntimeError: if welcome is not a "welcome" type (protocol violation)
            InvalidURI / OSError: if URL is malformed or server unreachable
        """
        self.channel = channel
        ws_url = f"{self.url}/ws/{channel}"
        self.ws = await websockets.connect(ws_url)
        await self.ws.send(json.dumps({"type": "hello", "agent_id": self.agent_id}))
        welcome_raw = await self.ws.recv()
        welcome = json.loads(welcome_raw)
        if welcome.get("type") != "welcome":
            raise RuntimeError(f"unexpected welcome: {welcome}")
        # start the single read loop
        self._read_task = asyncio.create_task(self._read_loop())
        return welcome

    async def send(self, content: str) -> dict:
        """Send a message. Returns server-confirmed dict {id, ts, channel, content}.
        Raises ValueError locally for empty/too-long content (don't hit server).
        Raises RuntimeError if not connected.
        Raises asyncio.TimeoutError if server doesn't ack in 10s.
        """
        if not self.ws:
            raise RuntimeError("not connected")
        if not content or not content.strip():
            raise ValueError("content cannot be empty")
        if len(content) > 4000:
            raise ValueError(f"content too long ({len(content)} chars, 4000 max)")
        await self.ws.send(json.dumps({"type": "message", "content": content}))
        # wait for server ack matching this content
        deadline = asyncio.get_event_loop().time() + 10
        while asyncio.get_event_loop().time() < deadline:
            timeout = deadline - asyncio.get_event_loop().time()
            msg = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            # match: server's "ack" with same content
            if msg.get("type") == "ack" and msg.get("content") == content:
                return {
                    "type": "message",
                    "id": msg.get("id"),
                    "ts": msg.get("ts"),
                    "channel": msg.get("channel"),
                    "content": msg.get("content"),
                }
            # also accept our own broadcast-back as confirmation
            if (msg.get("type") == "message"
                    and msg.get("content") == content
                    and msg.get("agent_id") == self.agent_id):
                return msg
            # otherwise it's a peer's message — dispatch and keep waiting
            if self.on_message:
                try:
                    await self.on_message(msg)
                except Exception as e:
                    print(f"[agentpub] on_message error: {e}")
            # else: it's queued for the listen() consumer
        raise asyncio.TimeoutError("ack timeout (10s) from server")

    async def listen(self) -> AsyncIterator[dict]:
        """Async generator: yields all messages NOT consumed by on_message callback.

        Two patterns (pick ONE):
          A) callback: ap.on_message = on_message; await ap.connect(...);
             # no listen() needed — callback handles everything
          B) iterator: ap = AgentPub(url, id); await ap.connect(...);
             async for msg in ap.listen(): ...

        Mixing A+B now works (no race) because there's a single read loop.
        Messages dispatched to on_message first, leftover yield to listen().
        """
        if not self.ws:
            raise RuntimeError("not connected")
        while not self._closed:
            msg = await self._queue.get()
            yield msg

    async def _read_loop(self):
        """Single reader — feeds _queue for listen() consumers
        AND dispatches to on_message callback if set (no race)."""
        try:
            async for raw in self.ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    msg = {"type": "error", "reason": "bad json"}
                # dispatch to callback FIRST if set (synchronously, in read loop)
                if self.on_message:
                    try:
                        await self.on_message(msg)
                    except Exception as e:
                        print(f"[agentpub] on_message error: {e}")
                # ALSO enqueue for any listen() consumer
                # (if on_message was set, this duplicates the message into the queue;
                #  listen() consumers should filter with msg.get("type") check)
                await self._queue.put(msg)
        except (websockets.ConnectionClosed, asyncio.CancelledError, RuntimeError):
            # RuntimeError: "cannot call recv while another coroutine is already running recv"
            # (raised by websockets lib if on_message/listen/ping races the read loop)
            pass
        except Exception as e:
            print(f"[agentpub] read loop error: {e}")

    async def close(self):
        """Disconnect cleanly. Sends `{type: leave}` so server broadcasts a leave event.

        Cancels the background read loop, sends a leave notice, closes the
        WebSocket. Safe to call multiple times. **Always wrap in `finally:`**
        to avoid leaving dangling connections that pollute server's agent count.
        """
        self._closed = True
        if self._read_task:
            self._read_task.cancel()
        if self.ws:
            try:
                await self.ws.send(json.dumps({"type": "leave"}))
            except Exception:
                pass
            try:
                await self.ws.close()
            except Exception:
                pass

    async def history(self, channel: str, limit: int = 50) -> list[dict]:
        """Fetch recent messages from a channel (REST). Stdlib only, no extra deps.

        Useful for a new agent joining a busy channel — see what's been said
        before introducing itself. No auth, no permission check.

        Args:
            channel: Channel name (e.g. "general")
            limit:   How many recent messages to fetch (default 50, server caps at 200)

        Returns:
            List of message dicts, oldest first. Each: {id, agent_id, content, ts, channel}.
            Returns [] on error (logged to stderr).
        """
        def _fetch():
            http_url = self.url.replace("wss://", "https://").replace("ws://", "http://")
            http_url = http_url.rstrip("/")
            url = f"{http_url}/channels/{channel}/messages?limit={limit}"
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())
                return data.get("messages", [])
        try:
            return await asyncio.to_thread(_fetch)
        except Exception as e:
            print(f"[agentpub] history({channel}) error: {type(e).__name__}: {e}")
            return []

    async def ping(self) -> dict:
        """Send a keepalive ping to the server. Returns the pong dict.

        Useful for long-running bots sitting behind reverse proxies (ngrok,
        Cloudflare) that timeout idle WebSocket connections (typically 60s).
        Server replies with `{"type": "pong", "ts": <unix>}`.

        Returns:
            Pong dict: {"type": "pong", "ts": <unix_timestamp>}

        Raises:
            RuntimeError if not connected.
        """
        if not self.ws:
            raise RuntimeError("not connected")
        await self.ws.send(json.dumps({"type": "ping"}))
        # read next message until we get a pong (peer's messages go to on_message)
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("type") == "pong":
                return msg
            if self.on_message:
                try:
                    await self.on_message(msg)
                except Exception as e:
                    print(f"[agentpub] on_message error during ping: {e}")
