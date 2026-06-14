#!/usr/bin/env python3
"""
AgentPub - GitHub repo creation via browser automation.

HALTS at 2FA / captcha. sampson handles those.

Usage:
    python3 deploy/github_create_via_browser.py
    (then sampson interacts when KAI halts)

Output:
    - Screenshots in docs/gh_*.png
    - Repo URL printed at end
    - GitHub URL written to .github_repo_url
"""
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, '/home/kali/桌面/agent/agentpub')
from agentpub.client import AgentPub  # uses websockets only

import websockets
from pyppeteer import connect

REPO_NAME = "agentpub"
REPO_DESCRIPTION = "Public chat for AI agents — WebSocket + JSON, 3-method SDK"
REPO_VISIBILITY = "public"  # 'public' or 'private'
LICENSE = "MIT"
ADD_README = True
ADD_LICENSE = True
ADD_GITIGNORE = "Python"

DOCS_DIR = Path("/home/kali/桌面/agent/agentpub/docs")
DOCS_DIR.mkdir(parents=True, exist_ok=True)


async def halt(page, reason: str, save_state: dict = None):
    """Stop everything. Screenshot. Print. Save state. Wait for sampson."""
    ts = int(time.time())
    screenshot = DOCS_DIR / f"gh_halt_{ts}.png"
    await page.screenshot({'path': str(screenshot), 'fullPage': True})
    state_file = DOCS_DIR / f"gh_state_{ts}.json"
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
    print("  1. 看截图 (上面路径)")
    print("  2. 处理 2FA / captcha / 任何阻塞")
    print("  3. 跟我说 'continue'")
    print()
    return state


async def main():
    print("=== GitHub repo creation via browser ===")
    print(f"目标: github.com/{sampson_username or '<your-user>'}/{REPO_NAME}")
    print(f"公开性: {REPO_VISIBILITY}")
    print()

    # 接 sampson Chrome 9222
    print("[1] 连接 sampson Chrome 9222 ...")
    try:
        browser = await connect(browserURL='http://localhost:9222', defaultViewport=None)
    except Exception as e:
        print(f"❌ 9222 连不上: {e}")
        print("sampson 你先跑: google-chrome --remote-debugging-port=9222 --user-data-dir=~/桌面/agent/chrome-debug")
        return
    print("    ✅ 已连")

    pages = await browser.pages()
    # 找或开新 tab
    target = None
    for p in pages:
        if 'github.com' in p.url:
            target = p
            break
    if not target:
        target = await browser.newPage()
        await target.goto('https://github.com/', {'waitUntil': 'networkidle2', 'timeout': 30000})
    await target.bringToFront()
    print(f"[2] 当前 tab: {target.url}")

    # 看是否已登录
    login_state = await target.evaluate('''() => {
        return {
            has_avatar: !!document.querySelector('img.avatar, [data-octo-click="avatar_click"]'),
            url: location.href,
            has_signin: !!document.querySelector('a[href*="/login"], a[href*="/signin"]'),
        };
    }''')
    print(f"    login state: {login_state}")

    if login_state.get('has_signin') and not login_state.get('has_avatar'):
        print("    ⚠️ 看起来未登录. 跳到 /login")
        await target.goto('https://github.com/login', {'waitUntil': 'networkidle2', 'timeout': 30000})
        await asyncio.sleep(2)
        # 2FA 节点
        if await target.querySelector('input[name="otp"]'):
            await halt(target, "2FA detected at github.com/login",
                      {"step": "login_2fa"})
            return
        await target.screenshot({'path': str(DOCS_DIR / "gh_01_login.png"), 'fullPage': True})
        print("    📸 gh_01_login.png — sampson 登录 (browser 已有 cookie 通常跳过)")

    # 跳到 /new
    print("[3] 跳到 https://github.com/new ...")
    await target.goto('https://github.com/new', {'waitUntil': 'networkidle2', 'timeout': 30000})
    await asyncio.sleep(2)

    # 2FA 检查 (整个流程)
    page_text = await target.evaluate('() => document.body.innerText')
    if 'two-factor' in page_text.lower() or 'verify code' in page_text.lower() or 'authentication code' in page_text.lower():
        await halt(target, "2FA detected on /new page",
                  {"step": "two_factor"})
        return

    await target.screenshot({'path': str(DOCS_DIR / "gh_02_new.png"), 'fullPage': True})
    print("    📸 gh_02_new.png")

    # 填表
    print("[4] 填表 ...")
    # Repository name
    name_input = await target.querySelector('input[name="repository[name]"]')
    if name_input:
        await name_input.click({'clickCount': 3})  # select all
        await name_input.type(REPO_NAME)
        print(f"    name: {REPO_NAME}")
    else:
        await halt(target, "找不到 repository name input")
        return

    # Description (optional)
    desc_input = await target.querySelector('input[name="repository[description]"]')
    if desc_input:
        await desc_input.type(REPO_DESCRIPTION)
        print(f"    desc: {REPO_DESCRIPTION}")

    # Public / Private
    if REPO_VISIBILITY == "public":
        # 默认就是 public, 但要确认 radio 选中
        try:
            await target.click('input[value="public"][type="radio"]')
        except Exception:
            pass  # 默认就是 public
    else:
        await target.click('input[value="private"][type="radio"]')

    # README
    if ADD_README:
        try:
            await target.click('input[name="repository[auto_init]"]')
            print("    README: ✅")
        except Exception:
            pass

    # .gitignore
    if ADD_GITIGNORE:
        try:
            await target.click('input[name="repository[gitignore_template]"]', {'clickCount': 1})
            # 打开 dropdown
            await asyncio.sleep(0.5)
            # 选 Python
            opt = await target.querySelector('input[value="Python"]')
            if opt:
                await opt.click()
                print("    .gitignore: Python")
        except Exception as e:
            print(f"    .gitignore 跳过: {e}")

    # License
    if ADD_LICENSE:
        try:
            await target.click('input[name="repository[license_template]"]', {'clickCount': 1})
            await asyncio.sleep(0.5)
            opt = await target.querySelector('input[value="mit"]')
            if opt:
                await opt.click()
                print("    license: MIT")
        except Exception as e:
            print(f"    license 跳过: {e}")

    await target.screenshot({'path': str(DOCS_DIR / "gh_03_filled.png"), 'fullPage': True})
    print("    📸 gh_03_filled.png — sampson 你看这截图, 确认无误后跟我说 'create'")

    # 不直接点 Create, 等 sampson 确认 (防止误操作)
    print()
    print("=" * 60)
    print("⏸️  暂停 — 等 sampson 确认")
    print("    看 gh_03_filled.png")
    print("    确认无误后跟我说 'create', 我才会点按钮")
    print("=" * 60)
    return  # 不点 Create, 等 sampson 二次确认

    # ===== 下面是 sampson 同意后才跑的 =====
    # create_button = await target.querySelector('button[type="submit"][data-disable-with="Creating repository..."]')
    # if not create_button:
    #     create_button = await target.querySelector('button:has-text("Create repository")')
    # await create_button.click()
    # await asyncio.sleep(3)
    # await target.screenshot({'path': str(DOCS_DIR / "gh_04_created.png"), 'fullPage': True})
    # print("    📸 gh_04_created.png")
    # final_url = target.url
    # print(f"    repo URL: {final_url}")
    # (DOCS_DIR.parent / ".github_repo_url").write_text(final_url)
    # print(f"    ✅ 已写到 {DOCS_DIR.parent / '.github_repo_url'}")


if __name__ == "__main__":
    sampson_username = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(main())
