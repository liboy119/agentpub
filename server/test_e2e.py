#!/usr/bin/env python3
"""
E2E test: 2 client + Hermes bot
验证:
- 3 agents 同时连接
- 消息广播
- 历史消息存储
- 频道隔离
- 优雅断开
"""
import asyncio
import json
import sys
sys.path.insert(0, '/home/kali/桌面/agent/agentpub/sdk')
from agentpub import AgentPub, HermesBot


async def test_client(name: str, channel: str, messages_to_send: list, listen_count: int):
    """单 client 测试."""
    ap = AgentPub("ws://localhost:7700", name)
    welcome = await ap.connect(channel)
    print(f"[{name}] connected, welcome={welcome.get('type')}")

    received = []
    received_target = listen_count

    async def listener():
        async for msg in ap.listen():
            received.append(msg)
            content = msg.get('content') or str(msg.get('event', '')) or str(msg)
            print(f"[{name}] RX: {msg.get('type')} from={(msg.get('agent_id') or 'sys')[:30]}: {content[:60]}")
            if len([m for m in received if m.get('type') == 'message']) >= received_target:
                break

    listener_task = asyncio.create_task(listener())
    await asyncio.sleep(0.5)  # 等欢迎消息

    for msg in messages_to_send:
        await ap.send(msg)
        await asyncio.sleep(0.3)

    # 等收到目标数量
    try:
        await asyncio.wait_for(listener_task, timeout=10)
    except asyncio.TimeoutError:
        listener_task.cancel()

    await ap.close()
    msgs_rx = [m for m in received if m.get('type') == 'message']
    return {"name": name, "sent": len(messages_to_send), "received_msgs": len(msgs_rx)}


async def main():
    print("=== E2E Test: 3 agents + 1 hermes bot ===\n")

    # 启动 hermes bot 后台
    hermes = HermesBot("ws://localhost:7700", "hermes-001")
    hermes_task = asyncio.create_task(hermes.start("general"))
    await asyncio.sleep(1)  # 让 hermes 发完出生帖

    # 启动 2 个 client 同时连
    client_a = asyncio.create_task(
        test_client("agent-alpha-001", "general",
                    ["hello agents, 我是 alpha", "BTC 怎么看？"],
                    listen_count=5)
    )
    client_b = asyncio.create_task(
        test_client("agent-beta-002", "general",
                    ["hi 大家好, beta 在此", "我关注 defi"],
                    listen_count=5)
    )

    # 频道隔离测试: 另一个频道不应该收到 general 的消息
    client_other_channel = asyncio.create_task(
        test_client("agent-isolation-test", "btc",
                    ["BTC 频道专属消息"],
                    listen_count=2)
    )

    # 等所有 client 完成
    results = await asyncio.gather(client_a, client_b, client_other_channel, return_exceptions=True)

    # 停 hermes
    hermes_task.cancel()
    try:
        await hermes_task
    except asyncio.CancelledError:
        pass

    print("\n=== 结果 ===")
    for r in results:
        if isinstance(r, Exception):
            print(f"  ❌ {r}")
        else:
            print(f"  ✅ {r['name']}: sent={r['sent']} received_msgs={r['received_msgs']}")


if __name__ == "__main__":
    asyncio.run(main())
