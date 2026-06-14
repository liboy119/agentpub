#!/usr/bin/env python3
"""
AgentPub - Cloudflare Tunnel creation via browser automation.

HALTS at 2FA / captcha. sampson handles those.

Usage:
    python3 deploy/cloudflare_tunnel_via_browser.py <TUNNEL_NAME>
    e.g. python3 deploy/cloudflare_tunnel_via_browser.py agentpub-prod

Output:
    - Screenshots in docs/cf_*.png
    - Tunnel UUID + token saved to .cloudflare_tunnel_credentials
    - /etc/cloudflared/config.yml written (after sampson confirms)
"""
import asyncio
import json
import sys
import time
from pathlib import Path

import websockets
from pyppeteer import connect

DOCS_DIR = Path("/home/kali/桌面/agent/agentpub/docs")
DOCS_DIR.mkdir(parents=True, exist_ok=True)


async def halt(page, reason: str, save_state: dict = None):
    """Halt and tell sampson."""
    ts = int(time.time())
    screenshot = DOCS_DIR / f"cf_halt_{ts}.png"
    await page.screenshot({'path': str(screenshot), 'fullPage': True})
    state_file = DOCS_DIR / f"cf_state_{ts}.json"
    state = {
        "reason": reason,
        "url": page.url,
        "title": await page.title(),
        "ts": ts,
        "screenshot": str(screenshot),
    }
    if save_state:
        state.update(save_state)
    state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    print()
    print("=" * 60)
    print(f"🚨 HALT: {reason}")
    print(f"   URL: {page.url}")
    print(f"   Screenshot: {screenshot}")
    print(f"   State: {state_file}")
    print("=" * 60)
    print()
    print("sampson 你的回合:")
    print("  1. 看截图")
    print("  2. 处理 2FA / captcha / Cloudflare verify")
    print("  3. 跟我说 'continue'")
    print()
    return state


async def main():
    if len(sys.argv) < 2:
        print("用法: python3 cloudflare_tunnel_via_browser.py <TUNNEL_NAME>")
        print("例:   python3 cloudflare_tunnel_via_browser.py agentpub-prod")
        sys.exit(1)
    tunnel_name = sys.argv[1]
    print(f"=== Cloudflare Tunnel 创建: {tunnel_name} ===\n")

    # 接 Chrome
    print("[1] 连接 sampson Chrome 9222 ...")
    try:
        browser = await connect(browserURL='http://localhost:9222', defaultViewport=None)
    except Exception as e:
        print(f"❌ 9222 连不上: {e}")
        print("sampson: google-chrome --remote-debugging-port=9222 --user-data-dir=~/桌面/agent/chrome-debug")
        return
    print("    ✅ 已连")

    # 找/开 cloudflare tab
    pages = await browser.pages()
    target = None
    for p in pages:
        if 'cloudflare.com' in p.url:
            target = p
            break
    if not target:
        target = await browser.newPage()

    await target.bringToFront()

    # 跳到 dashboard
    print("[2] 跳到 dash.cloudflare.com ...")
    await target.goto('https://dash.cloudflare.com/', {'waitUntil': 'networkidle2', 'timeout': 30000})
    await asyncio.sleep(3)

    # 2FA / 登录检查
    page_text = await target.evaluate('() => document.body.innerText')
    page_url = target.url

    if 'verify' in page_url.lower() or 'two-factor' in page_text.lower() or 'authentication code' in page_text.lower():
        await halt(target, "Cloudflare 2FA 页面",
                  {"step": "cloudflare_2fa", "expected_after": "Zero Trust > Networks > Tunnels"})
        return

    if 'login' in page_url.lower() and 'sign' in page_text.lower():
        await halt(target, "需要 sampson 登录 Cloudflare (含 2FA)",
                  {"step": "cloudflare_login", "expected_after": "Zero Trust > Networks > Tunnels"})
        return

    await target.screenshot({'path': str(DOCS_DIR / "cf_01_dashboard.png"), 'fullPage': True})
    print("    📸 cf_01_dashboard.png")

    # 跳到 Tunnels
    # Cloudflare 现在叫 Zero Trust, 路径: Zero Trust > Networks > Tunnels
    print("[3] 跳到 Tunnels (Zero Trust > Networks > Tunnels) ...")
    tunnels_url = "https://one.dash.cloudflare.com/"  # Zero Trust 默认
    # 但我们不知道 sampson 账号, account ID 没法拼. 用 click 走菜单.
    try:
        # 找 Zero Trust link
        zt_link = await target.querySelector('a[href*="zero-trust"], a[href*="/access"], a:has-text("Zero Trust")')
        if zt_link:
            await zt_link.click()
            await asyncio.sleep(3)
            print("    ✅ Zero Trust 页")
        else:
            print("    ⚠️ 找不到 Zero Trust 链接, 试试直接进")
            await target.goto('https://one.dash.cloudflare.com/', {'waitUntil': 'networkidle2', 'timeout': 30000})
            await asyncio.sleep(3)
    except Exception as e:
        print(f"    菜单点击失败, 直接进: {e}")
        await target.goto('https://one.dash.cloudflare.com/', {'waitUntil': 'networkidle2', 'timeout': 30000})
        await asyncio.sleep(3)

    # 找 Networks > Tunnels
    print("[4] 找 Tunnels 子菜单 ...")
    try:
        # 多重 fallback
        for selector in ['a:has-text("Tunnels")', 'a[href*="tunnels"]', 'a:has-text("Networks")']:
            link = await target.querySelector(selector)
            if link:
                await link.click()
                await asyncio.sleep(3)
                print(f"    ✅ 点了 {selector}")
                break
        else:
            print("    ⚠️ 找不到 Tunnels 链接, 尝试 URL ...")
            # 一个常见 URL 模式 (Cloudflare 改了 N 次)
            await target.goto(target.url.split('/')[0] + '//one.dash.cloudflare.com/networks/tunnels',
                              {'waitUntil': 'networkidle2', 'timeout': 30000})
            await asyncio.sleep(3)
    except Exception as e:
        await halt(target, f"找不到 Tunnels 菜单: {e}", {"step": "find_tunnels"})
        return

    await target.screenshot({'path': str(DOCS_DIR / "cf_02_tunnels_list.png"), 'fullPage': True})
    print("    📸 cf_02_tunnels_list.png — sampson 看截图, 确认是 Tunnels 列表页")

    # 暂停 — 等 sampson 二次确认
    print()
    print("=" * 60)
    print("⏸️  暂停 — 等 sampson 确认")
    print("    看 cf_02_tunnels_list.png")
    print("    确认在 Tunnels 页后跟我说 'create tunnel'")
    print("    我会点 'Create a tunnel' 按钮 + 填名字 + 走流程")
    print("=" * 60)
    return  # 不点, 等 sampson

    # ===== 下面是 sampson 同意后才跑的 =====
    # try:
    #     create_btn = await target.querySelector('button:has-text("Create a tunnel")')
    #     if not create_btn:
    #         create_btn = await target.querySelector('a:has-text("Create a tunnel")')
    #     await create_btn.click()
    #     await asyncio.sleep(2)
    # except Exception as e:
    #     await halt(target, f"找不到 Create a tunnel 按钮: {e}", {"step": "create_button"})
    #     return
    #
    # # 填 tunnel 名字
    # name_input = await target.querySelector('input[name="name"], input[placeholder*="tunnel"]')
    # if name_input:
    #     await name_input.type(tunnel_name)
    # await target.screenshot({'path': str(DOCS_DIR / "cf_03_name.png"), 'fullPage': True})
    #
    # # 保存 token (从页面 copy)
    # token = await target.evaluate('''() => {
    #     const codeEl = document.querySelector('pre, code, .token, [class*="token"]');
    #     return codeEl ? codeEl.innerText : null;
    # }''')
    # if token:
    #     creds = DOCS_DIR.parent / ".cloudflare_tunnel_credentials"
    #     creds.write_text(json.dumps({"tunnel_name": tunnel_name, "token": token}, indent=2))
    #     print(f"    ✅ token 已存 {creds}")


if __name__ == "__main__":
    asyncio.run(main())
