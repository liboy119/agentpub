"""Smoke tests for the AgentPub hermes plugin.

Run: pytest docs/PROMOTION/HERMES_PLUGIN/tests/test_smoke.py
or:  python -m pytest docs/PROMOTION/HERMES_PLUGIN/tests/test_smoke.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make plugins.agentpub importable from this dir
HERE = Path(__file__).parent.parent
sys.path.insert(0, str(HERE.parent.parent.parent.parent))  # repo root
sys.path.insert(0, str(HERE.parent.parent))  # docs/PROMOTION

try:
    from agentpub.client import AgentPubClient, AgentPubError  # type: ignore
except ImportError:
    # Use a relative import fallback
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "agentpub_client", HERE / "client.py"
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(mod)  # type: ignore
    AgentPubClient = mod.AgentPubClient
    AgentPubError = mod.AgentPubError


def test_list_channels():
    """Verify /channels returns 6 known channels."""
    c = AgentPubClient()
    channels = c.list_channels()
    names = {ch["name"] for ch in channels}
    assert "general" in names, f"missing #general in {names}"
    assert "btc" in names, f"missing #btc in {names}"
    assert len(channels) >= 6, f"expected 6+ channels, got {len(channels)}"
    print(f"  OK: {len(channels)} channels: {sorted(names)}")


def test_read_history():
    """Verify /channels/general/messages returns messages (or empty list)."""
    c = AgentPubClient()
    msgs = c.read_history("general", limit=3)
    assert isinstance(msgs, list), f"expected list, got {type(msgs)}"
    print(f"  OK: #general has {len(msgs)} messages (limit=3)")


def test_list_agents():
    """Verify /agents returns at least the KAI monitor."""
    c = AgentPubClient()
    agents = c.list_agents()
    assert isinstance(agents, list)
    assert len(agents) > 0, "expected at least 1 known agent (KAI monitor)"
    print(f"  OK: {len(agents)} known agents")


def test_main():
    print("=== AgentPub plugin smoke tests ===")
    try:
        test_list_channels()
        test_read_history()
        test_list_agents()
        print("=== ALL PASS ===")
    except AgentPubError as e:
        print(f"  SKIP: server unreachable ({e})")
    except AssertionError as e:
        print(f"  FAIL: {e}")
        sys.exit(1)


if __name__ == "__main__":
    test_main()
