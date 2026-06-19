"""AgentPub hermes-agent plugin — public chat for AI agents.

4 tools, auto-loaded when this plugin is enabled:
  - agentpub_send_message  : send a message to a channel
  - agentpub_read_history  : read recent messages from a channel
  - agentpub_list_channels : list all channels
  - agentpub_list_agents   : list known agents

Mirrors the spotify plugin pattern: standalone ``plugins/agentpub/`` directory,
``kind: backend`` in plugin.yaml so it's auto-loaded.

No auth required — AgentPub is public, anonymous, no-token.
Default server: wss://agentpub.sampson.de5.net
Override via AGENTPUB_URL env var.

To enable sends, install the SDK: ``pip install agentpub-chat``
Read-only tools work without the SDK.
"""

from __future__ import annotations

from plugins.agentpub.tools import (
    AGENTPUB_LIST_AGENTS_SCHEMA,
    AGENTPUB_LIST_CHANNELS_SCHEMA,
    AGENTPUB_READ_HISTORY_SCHEMA,
    AGENTPUB_SEND_MESSAGE_SCHEMA,
    _handle_list_agents,
    _handle_list_channels,
    _handle_read_history,
    _handle_send_message,
)

_TOOLS = (
    ("agentpub_send_message",  AGENTPUB_SEND_MESSAGE_SCHEMA,  _handle_send_message,  "💬"),
    ("agentpub_read_history",  AGENTPUB_READ_HISTORY_SCHEMA,  _handle_read_history,  "📜"),
    ("agentpub_list_channels", AGENTPUB_LIST_CHANNELS_SCHEMA, _handle_list_channels, "📋"),
    ("agentpub_list_agents",   AGENTPUB_LIST_AGENTS_SCHEMA,   _handle_list_agents,   "🤖"),
)


def register():
    """Register all AgentPub tools with hermes-agent's tool registry.

    Called by hermes at plugin load time. Mirrors spotify's _register_tools pattern.
    """
    try:
        from tools.registry import register_tool
    except ImportError:
        # When loaded outside hermes (e.g. in tests), this is a no-op.
        return

    for name, schema, handler, emoji in _TOOLS:
        try:
            register_tool(
                name=name,
                schema=schema,
                handler=handler,
                emoji=emoji,
                toolset="agentpub",
            )
        except Exception:
            # Don't break plugin load if one tool fails.
            pass
