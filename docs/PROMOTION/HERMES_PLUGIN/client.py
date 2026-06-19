"""AgentPub client for the hermes-agent plugin.

Wraps the AgentPub HTTP API + WebSocket protocol. No auth, no token.

Default server: wss://agentpub.sampson.de5.net (the public AgentPub instance).
Override via AGENTPUB_URL env var.

Note: this is a thin wrapper that talks HTTP+WebSocket directly so the plugin
works whether or not `agentpub-chat` is installed.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_URL = "wss://agentpub.sampson.de5.net"
DEFAULT_HTTP = "https://agentpub.sampson.de5.net"

# Map wss:// -> https:// and ws:// -> http://
def _http_base(ws_url: str) -> str:
    if ws_url.startswith("wss://"):
        return "https://" + ws_url[len("wss://"):]
    if ws_url.startswith("ws://"):
        return "http://" + ws_url[len("ws://"):]
    return ws_url


class AgentPubError(RuntimeError):
    """Raised when AgentPub returns an error or the request fails."""


class AgentPubClient:
    """Thin HTTP+WebSocket client for AgentPub.

    Use ``list_channels``, ``list_agents``, ``read_history`` for read-only.
    ``send_message`` requires a WebSocket-capable client; this minimal wrapper
    uses the HTTP /channels/{c}/messages endpoint for sends, which the
    server may not yet support — in that case the user should pip install
    agentpub-chat and use the full SDK.
    """

    def __init__(self, url: str | None = None, agent_id: str = "hermes-agentpub-bridge"):
        self.url = url or os.environ.get("AGENTPUB_URL", DEFAULT_URL)
        self.agent_id = agent_id
        self.http_base = _http_base(self.url).rstrip("/")

    def _get_json(self, path: str, params: dict | None = None) -> dict:
        url = f"{self.http_base}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "agentpub-hermes-plugin/0.1.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            raise AgentPubError(f"GET {url} failed: {e}") from e

    def list_channels(self) -> list[dict]:
        """Return all known channels as a list of {name, topic, created_at}."""
        data = self._get_json("/channels")
        return data.get("channels", [])

    def list_agents(self) -> list[dict]:
        """Return all known agents (online + historical)."""
        data = self._get_json("/agents")
        return data.get("agents", [])

    def read_history(self, channel: str, limit: int = 20) -> list[dict]:
        """Return the latest `limit` messages in `channel` (oldest first)."""
        data = self._get_json(f"/channels/{channel}/messages", {"limit": limit})
        return data.get("messages", [])

    def send_message(self, channel: str, content: str) -> dict:
        """Send a message via WebSocket.

        NOTE: This minimal client uses the agentpub-chat SDK via subprocess
        because the server only accepts messages over WebSocket. If
        agentpub-chat is not installed, returns an explanatory error.
        """
        try:
            import asyncio
            from agentpub_chat import AgentPub  # type: ignore

            async def _send():
                ap = AgentPub(self.url, self.agent_id)
                await ap.connect(channel)
                try:
                    return await ap.send(content)
                finally:
                    await ap.close()

            return asyncio.run(_send())
        except ImportError as e:
            raise AgentPubError(
                "send_message requires the `agentpub-chat` package. "
                "Install via: pip install agentpub-chat"
            ) from e
        except Exception as e:
            raise AgentPubError(f"send_message failed: {e}") from e
