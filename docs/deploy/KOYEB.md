# Koyeb Deployment Guide for sampson (7/9)
## 5 steps, ~5 minutes

### Step 1: signup
https://app.koyeb.com/signup
- 用 GitHub OAuth (liboy119 推荐)
- 不需信用卡

### Step 2: 创建 Koyeb Service
1. 登录后 https://app.koyeb.com/services/new
2. 选择 GitHub deployment
3. 选 liboy119/agentpub 仓库
4. branch: main
5. builder: Dockerfile -> Dockerfile name: Dockerfile (Koyeb 自动找)
   或 builder: Buildpack (Koyeb 自动 python)

### Step 3: 配置 Service
- Region: Frankfurt (fra) - 离欧洲 mcp.so 较近
- Instance type: eco (FREE) - 0.25 vCPU + 1 GB RAM
- Port: 8080
- Health check path: /kai/cron-status
- Env vars:
  PORT=8080
  PYTHONUNBUFFERED=1

### Step 4: 部署 + 拿 URL
- 点 Deploy
- Koyeb 给一个 URL: https://agentpub-<username>.koyeb.app

### Step 5: 验证
curl https://agentpub-<username>.koyeb.app/agents
curl https://agentpub-<username>.koyeb.app/skills

然后 sampson 把 URL paste 给 KAI, 我会改 install.sh / mcp.json / README + push

## Eco tier 限制:
- 5h 后 sleep, 下次访问会冷启动 (~10s)
- 0.25 vCPU + 1 GB RAM
- 1 GB 持久化 storage
- 10 GB / 月 bandwidth

## 为什么 Eco tier 就够我们:
- AgentPub 7/9 真流量 = 1 user (sampson 你 + KAI + 偶尔 CZ + 笔记本)
- 1 GB RAM 跑 FastAPI + uvicorn + sqlite 足够
