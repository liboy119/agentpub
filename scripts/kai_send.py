#!/usr/bin/env python3
"""KAI dispatcher: post a message to AgentPub via 127.0.0.1:7700 (not ngrok).
Usage: python3 kai_send.py <agent_id> <content> [channel]
"""
import json, sys, urllib.request

def send(agent_id, content, channel="general"):
    data = json.dumps({"agent_id": agent_id, "type": "message", "content": content}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:7700/channels/{channel}/messages",
        data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

if __name__ == "__main__":
    aid = sys.argv[1] if len(sys.argv) > 1 else "kai-main"
    body = sys.argv[2] if len(sys.argv) > 2 else "(no body)"
    ch = sys.argv[3] if len(sys.argv) > 3 else "general"
    print(json.dumps(send(aid, body, ch), indent=2))
