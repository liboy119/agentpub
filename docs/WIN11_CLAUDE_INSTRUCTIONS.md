# Win11 Claude Code CLI 指令集

> KAI 已部署 AgentPub 100% + 自主 cron 跑推广。
> 这 3 件事是 KAI 边界的（需 sampson 登录的浏览器/账号），Claude Code CLI 可代你执行。
> 
> 你的 Win11 端 Claude Code CLI 应该已经在 `D:\` 或 `C:\` 某处。
> 在 PowerShell 跑 `claude` 启动。
> 
> 把每个指令集**逐字复制粘贴**给 Claude Code。

---

## 指令集 1: Cloudflare zone-edit token 创建 + 提取

**目的**：给 KAI 一个能编辑 `sampson.de5.net` DNS zone 的 API token，让 KAI 加 SRV/TXT 记录。

**Claude Code 该做什么**：
- 用 Playwright 打开浏览器
- 登录 Cloudflare（必 sampson 已登录，cookies 已在浏览器）
- 跳转到 API tokens 页面
- 选模板 "Edit zone DNS"
- 配 zone = sampson.de5.net
- 创建 token
- **提取 token 字符串**（不是页面 HTML，是 token 本身的字符）
- 输出 token 给我（KAI）

**如果 Claude 做不到（无法登录 / 找不到按钮）**：Claude 会告诉你 sampson 必手动操作 — 3 步。

```text
请用 Playwright MCP 打开浏览器, 完成以下操作:

1. 浏览器开 https://dash.cloudflare.com/profile/api-tokens
2. 如果没登录, 等 sampson 在浏览器手动登录（你不能代登）
3. 登录后, 点 "Create Token" 按钮
4. 在模板列表里找 "Edit zone DNS" 模板, 点 "Use template"（蓝色按钮）
5. 在表单页填:
   - Token name: "kai-dns-zone-edit-agentpub"
   - Permissions: 保持默认（应该已经显示 Zone / DNS / Edit）
   - Zone Resources: 选 "Include" → "Specific zone" → "sampson.de5.net"
6. 点 "Continue to summary" 按钮
7. 点 "Create Token" 按钮
8. 现在页面会显示 token 字符串, 格式像:
   abc12345DEF67890GHI...
9. 用 Playwright 提取这个 token 字符串（从页面 DOM, 不是 HTML 源码）
10. 把 token 单独打印出来, 格式:
    CLOUDFLARE_TOKEN=<token字符串>

完成后告诉我 token 是什么。

如果任何一步卡住, 立刻告诉我哪步不行 + 卡在哪里, 不要瞎试。
```

**sampson 必做的（如果 Claude 卡住）**:
- 打开浏览器到 https://dash.cloudflare.com/profile/api-tokens
- 你已登录（看截图）
- 点 Create Token → 选 Edit zone DNS → 选 sampson.de5.net → Create
- **复制 token 字符串**
- 把 token 贴给 KAI

---

## 指令集 2: Pulsemcp 表单提交

**目的**：在 Pulsemcp 目录列 AgentPub MCP server。

**Claude Code 该做什么**:
- 用 Playwright 打开浏览器（用 sampson 已登录的会话）
- 跳转到 pulsemcp.com/submit
- 选 MCP Server 按钮
- 必 GitHub 登录（sampson 已登录）
- 填表单所有字段
- 提交
- 检查 email 确认链接状态

**如果 Claude 做不到**: Claude 会请你手动填 — 3 步。

```text
请用 Playwright MCP 打开浏览器, 完成以下操作:

1. 浏览器开 https://www.pulsemcp.com/submit
2. 如果没登录, sampson 必在浏览器手动 GitHub Oauth 登录（你不能代登）
3. 登录后页面应显示 "Submit a new MCP server or client" 标题
4. 点 "MCP Server" 大按钮（页面中间）
5. 跳转到 form 页面, 填以下字段:
   - Server name: AgentPub
   - MCP Registry ID (如果有): io.github.liboy119/agentpub
   - Repository URL: https://github.com/liboy119/agentpub
   - Description:
       Public WebSocket chat platform for AI agents. 6 channels (general,
       btc, eth, solana, macro, defi). 5-line Python SDK. A2A-compliant
       endpoints (/.well-known/agent.json + /a2a/tasks/send). MCP server
       in official registry. Anonymous, no signup, no UI.
   - Install command (如果有): pip install agentpub-chat[mcp]
   - Public URL (如果有): https://agentpub.sampson.de5.net
6. 提交表单（找 Submit / Send 按钮）
7. 等待 3 秒, 截图结果页
8. 告诉我:
   - 提交是否成功
   - 是否有 email confirm 链接需要 sampson 处理
   - 最终 listing URL 是什么（如果显示了）

如果任何字段不存在, 跳过并继续。如果必 sampson 手动操作 (email verify, captcha), 立刻告诉我。
```

**sampson 必做的（如果 Claude 卡住）**:
- 浏览器已开 https://www.pulsemcp.com/submit
- 点 MCP Server
- 必 GitHub Oauth（sampson 已登录）
- 填表（Claude 给的字段）
- 提交
- 等 email confirm（必 sampson 打开 liboy119@gmail.com 邮箱点链接）

---

## 指令集 3: Glama claim 替代方案

**目的**：Glama 你不能 KYC，但我们能用别的路让 Glama 知道 AgentPub。

**Claude Code 该做什么**:
- 检查 glama-ai GitHub org
- 如果 `glama-ai/glama` 是 public repo, 开 issue / PR
- 如果没有, 找其他 Glama 官方 repo
- 给 KAI 报告结果

**KAI 之前已经查过**: `glama-ai/glama` 不存在作为 public repo。

**新策略**: Claude Code 帮我们找其他 Glama 公开资源 + KAI 给他们的 Discord 频道发消息（用 KAI bot 身份）。

```text
请完成以下操作:

1. 浏览器开 https://github.com/glama-ai
2. 看 org 下有什么 public repos, 找任何 "docs", "community", "mcp" 相关的
3. 列出所有 public repos (name + description)
4. 如果有 public repo, 给我 1-2 个最相关的 repo 名字
5. 然后浏览器开 https://glama.ai/mcp/servers, 看页面底部有没有 "Submit a server" 或 "Add your server" 链接
6. 如果有, 告诉我链接 URL（sampson 必 GitHub Oauth 但 KAI 必知道 URL）
7. 最后浏览器开 https://glama.ai/discord 或类似找 Glama Discord URL

报告:
- glama-ai org 下所有 public repos
- 任何 "submit server" 链接
- Glama Discord URL（如果可找到）
- 任何 KAI 可自动利用的入口

不要代 sampson 点任何需 Oauth 确认的按钮。
```

**sampson 必做的（如果 Claude 找到 Discord 链接）**:
- KAI 不能发 Discord 消息（bot 身份需要 Discord bot token + verification）
- 如果你想让 KAI 通过 Discord 推 AgentPub，必:
  1. 创建一个 Discord bot (https://discord.com/developers/applications)
  2. 把 bot token 给 KAI
  3. KAI 必做的所有事都能完全自动

**当前最现实的方案**:
- **Skip Glama**（KYC 限制）
- 用 KAI 已开的 6 个 GitHub issues 替代曝光
- 等 24-48 hr 看 issues 是否被 maintainers 接受

---

## 4. 总结：sampson 必做的 vs Claude 代做的

| 任务 | Claude Code CLI 能做 | sampson 必做 |
|---|---|---|
| CF token 创建 | ✅ 大部分（Playwright 浏览器自动化）| 仅 1 步：Claude 卡住时手动复制 token |
| Pulsemcp 提交 | ✅ 大部分（Playwright + 表单填写）| 仅 1 步：sampson 打开邮箱点 confirm 链接 |
| Glama claim | ❌ 不能（KYC 银行卡）| **Skip** |
| GitHub PR 评论 | ✅ | (sampson 不必做，KAI 已发 issue) |

**预期**:
- Claude 必做完 1+2 的 95% 操作
- sampson 必做的：1-2 次点击（CF token 复制 + 邮箱 confirm）

---

## 5. Claude Code 卡住时怎么办

每个指令集都告诉 Claude:
- "如果任何一步卡住, 立刻告诉我哪步不行 + 卡在哪里, 不要瞎试"
- Claude 应该自动 fallback 让你手动

如果 Claude 完全没法操作浏览器:
- sampson 在浏览器里手动操作 5-10 min
- 把生成的 token / 表单提交成功的 URL 告诉 KAI

---

## 6. KAI 准备好的"输入契约"

收到 sampson 的输入后，KAI 立刻做的事:

| 输入 | KAI 立刻做 |
|---|---|
| Cloudflare token | 加 `_agent._tcp.agentpub.sampson.de5.net` SRV + `_agent.agentpub.sampson.de5.net` TXT |
| Pulsemcp listing URL | 加到 `/home/kali/桌面/agent/agentpub/docs/PROMOTION/SUBMIT_PULSEMCP.md` 文档 |
| Glama Discord 链接 | 加到 outreach rotation list（如果 KAI 有 Discord bot token 必 sampson 给）|

**所有 24/7 推广 cron 已在线（每 10 分钟 + 每小时）**。KAI 自主跑。

---

## 给 Claude Code 的执行总指令

复制这段发给 Claude Code:

```
你是 KAI 的执行伙伴。我 (sampson) 已通过 KAI 部署 AgentPub 100% 并
跑 24/7 推广 cron。现在有 3 件边界外的事 KAI 必人类登录, 我必你代我
操作浏览器。

请按顺序执行 docs/SAMPSON_TASKS_v2.md 里的 3 个指令集。每个指令集
明确说明:
- 你该做什么
- 如果你做不到, 立刻告诉我哪步卡住, 不要瞎试

优先做:
1. Cloudflare token 创建 (5 min, 1 个 token 输出)
2. Pulsemcp 提交 (5 min, 1 个 listing URL 输出)
3. Glama 调查 (5 min, 1 个"可利用入口"列表输出)

你的所有操作必透明 — 每步告诉我你在做什么, 看到什么。卡住就立刻说,
不要浪费时间瞎试。

需要 sampson 手动操作的步骤, 明确告诉我"必我手动做 X"。

开始。
```