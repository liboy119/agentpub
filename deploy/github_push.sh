#!/bin/bash
# AgentPub - GitHub 推送命令模板
# sampson 给 GitHub 仓库地址后, 把 $REPO_URL 替换为实际地址
# 例: REPO_URL=git@github.com:liboy119/agentpub.git
#      REPO_URL=https://github.com/liboy119/agentpub.git
set -e

REPO_URL="${1:?用法: $0 <git-repo-url> [visibility]}"

cd /home/kali/桌面/agent/agentpub

echo "=== 1. 准备 .gitignore ==="
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
*.pyo
*.egg-info/
build/
dist/
*.db
*.db-journal
.env
.venv/
venv/
.idea/
.vscode/
.DS_Store
*.log
EOF
echo "  ✅ .gitignore"

echo ""
echo "=== 2. 准备 LICENSE (MIT) ==="
cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2026 Sampson Li

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF
echo "  ✅ LICENSE"

echo ""
echo "=== 3. git init + add + commit ==="
git init -b main
git config user.email "sbcalaiboy@gmail.com"
git config user.name "Sampson Li"
git add .
git commit -m "AgentPub v0.1.0 - public chat for AI agents

- FastAPI + WebSocket server with SQLite persistence
- 3-method Python SDK: connect() / send() / listen()
- HermesBot: autonomous first user, hosts #general
- 6 channels: general, btc, eth, solana, macro, defi
- E2E test with 3 clients + 1 hermes bot
- pip-installable via pyproject.toml
- LLM-readable onboarding doc for agent self-integration
- Cloudflare Tunnel deploy scripts"
echo "  ✅ commit"

echo ""
echo "=== 4. 加 remote + push ==="
git remote add origin "$REPO_URL"
echo "  remote: $REPO_URL"
git push -u origin main
echo ""
echo "  ✅ push 完成"
echo ""
echo "=== 5. 后续提交时 ==="
echo "  git add ."
echo "  git commit -m '...'"
echo "  git push"
