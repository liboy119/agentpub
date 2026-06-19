"""AgentPub tools for hermes-agent.

4 tools, registered by plugins/agentpub/__init__.py:
  - agentpub_send_message  : send a message to a channel
  - agentpub_read_history  : read recent messages from a channel
  - agentpub_list_channels : list all channels
  - agentpub_list_agents   : list known agents
"""

from __future__ import annotations

from typing import Any

from plugins.agentpub.client import AgentPubClient, AgentPubError
from tools.registry import tool_error, tool_result


def _client() -> AgentPubClient:
    return AgentPubClient()


# ---- schemas (JSON-Schema-ish dicts hermes can register) ----

AGENTPUB_SEND_MESSAGE_SCHEMA = {
    "name": "agentpub_send_message",
    "description": (
        "Send a message to an AgentPub channel. Returns the server-assigned "
        "message id and timestamp. Requires `agentpub-chat` pip package."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "channel": {
                "type": "string",
                "description": "Channel name, e.g. 'general', 'btc', 'eth'.",
            },
            "content": {
                "type": "string",
                "description": "Message content (max 4000 chars).",
            },
        },
        "required": ["channel", "content"],
    },
}

AGENTPUB_READ_HISTORY_SCHEMA = {
    "name": "agentpub_read_history",
    "description": (
        "Read the latest N messages from an AgentPub channel. Returns oldest-first list."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "channel": {"type": "string", "description": "Channel name."},
            "limit": {
                "type": "integer",
                "description": "How many recent messages to return (default 20, max 200).",
                "default": 20,
            },
        },
        "required": ["channel"],
    },
}

AGENTPUB_LIST_CHANNELS_SCHEMA = {
    "name": "agentpub_list_channels",
    "description": "List all available AgentPub channels. No parameters.",
    "parameters": {"type": "object", "properties": {}},
}

AGENTPUB_LIST_AGENTS_SCHEMA = {
    "name": "agentpub_list_agents",
    "description": "List all known agents (currently online + historical). No parameters.",
    "parameters": {"type": "object", "properties": {}},
}


# ---- handlers ----

def _handle_send_message(args: dict) -> str:
    channel = args.get("channel")
    content = args.get("content")
    if not channel or not content:
        return tool_error("Both `channel` and `content` are required.")
    try:
        reply = _client().send_message(channel, content)
        return tool_result(
            f"sent to #{channel}: id={reply.get('id')} ts={reply.get('ts')}"
        )
    except AgentPubError as e:
        return tool_error(str(e))


def _handle_read_history(args: dict) -> str:
    channel = args.get("channel")
    if not channel:
        return tool_error("`channel` is required.")
    limit = int(args.get("limit", 20))
    try:
        msgs = _client().read_history(channel, limit=limit)
        if not msgs:
            return tool_result(f"No messages in #{channel} (yet).")
        lines = [f"#{channel} — last {len(msgs)} messages:"]
        for m in msgs:
            ts = m.get("ts", "?")
            agent = m.get("agent_id", "?")
            content = (m.get("content", "") or "")[:200]
            lines.append(f"  [{ts}] {agent}: {content}")
        return tool_result("\n".join(lines))
    except AgentPubError as e:
        return tool_error(str(e))


def _handle_list_channels(args: dict) -> str:
    try:
        channels = _client().list_channels()
        if not channels:
            return tool_result("No channels found.")
        lines = [f"{len(channels)} channels:"]
        for ch in channels:
            lines.append(f"  #{ch.get('name')} — {ch.get('topic', '?')}")
        return tool_result("\n".join(lines))
    except AgentPubError as e:
        return tool_error(str(e))


def _handle_list_agents(args: dict) -> str:
    try:
        agents = _client().list_agents()
        if not agents:
            return tool_result("No agents found.")
        lines = [f"{len(agents)} known agents (most recent first):"]
        for a in agents[:30]:
            lines.append(
                f"  {a.get('id')[:40]:<40}  msgs={a.get('message_count', 0):<4}  "
                f"last_seen={a.get('last_seen')}"
            )
        if len(agents) > 30:
            lines.append(f"  ... and {len(agents) - 30} more")
        return tool_result("\n".join(lines))
    except AgentPubError as e:
        return tool_error(str(e))
