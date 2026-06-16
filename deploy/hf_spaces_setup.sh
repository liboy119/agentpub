#!/bin/bash
# AgentPub HF Spaces setup script
# ----------------------------------------------------------------------
# Usage:
#   export HF_TOKEN="hf_xxxxxxxxxxxx"
#   ./hf_spaces_setup.sh
#
# Required env:
#   HF_TOKEN     sampson's Hugging Face token (fine-grained, repo.write scope)
#
# What it does:
#   1. Verifies HF token via whoami-v2
#   2. Configures git remote `hf` (token NOT stored in .git/config — uses
#      one-shot push URL instead, so token never persists to disk)
#   3. Commits Dockerfile + requirements.txt + README + server/ + agentpub/
#      + deploy/ + docs/ + pyproject.toml
#   4. Pushes to https://huggingface.co/spaces/sampson119/agentpub main
#   5. Reports build status
#
# Why no remote URL: storing token in remote URL leaks it via .git/config
# and git log --all. KAI's improvement over sampson's original brief.
# ----------------------------------------------------------------------

set -e
cd "$(dirname "$0")/.."

# Validate
if [ -z "$HF_TOKEN" ]; then
    echo "ERROR: HF_TOKEN env not set"
    echo "  export HF_TOKEN='hf_...'"
    exit 1
fi

# 1. Verify token
echo "============================================================"
echo "  AgentPub HF Spaces Deploy"
echo "============================================================"
echo ""
echo "[1/5] Verifying HF token via whoami-v2..."
WHOAMI=$(curl -sS -H "Authorization: Bearer $HF_TOKEN" --max-time 10 https://huggingface.co/api/whoami-v2)
USERNAME=$(echo "$WHOAMI" | python3 -c "import sys, json; print(json.loads(sys.stdin.read())['name'])" 2>/dev/null || echo "ERROR")
if [ "$USERNAME" != "sampson119" ]; then
    echo "ERROR: token belongs to '$USERNAME' (expected 'sampson119')"
    exit 1
fi
echo "  ✓ token belongs to sampson119"

# 2. Verify Space exists
echo ""
echo "[2/5] Checking HF Space exists..."
SPACE=$(curl -sS -H "Authorization: Bearer $HF_TOKEN" --max-time 10 https://huggingface.co/api/spaces/sampson119/agentpub 2>/dev/null)
if echo "$SPACE" | grep -q "sampson119/agentpub"; then
    echo "  ✓ Space sampson119/agentpub exists"
else
    echo "ERROR: Space sampson119/agentpub not found. Create it first:"
    echo "  curl -X POST -H 'Authorization: Bearer \$HF_TOKEN' \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"name\":\"agentpub\",\"organization\":\"sampson119\",\"type\":\"space\",\"sdk\":\"docker\"}' \\"
    echo "    https://huggingface.co/api/repos/create"
    exit 1
fi

# 3. Stage files (HF Spaces needs Dockerfile + README + source)
echo ""
echo "[3/5] Staging files..."
git add Dockerfile requirements.txt README.md server/ agentpub/ deploy/ docs/ pyproject.toml
# Check if anything to commit
if git diff --cached --quiet; then
    echo "  ✓ no changes to commit (already deployed?)"
else
    git -c user.name="KAI" -c user.email="kai@agentpub.local" commit -m "deploy: HF Spaces initial release (v0.1.4 + port 7700)

- Dockerfile: python 3.13-slim, EXPOSE 7700, CMD server.main
- requirements.txt: extracted from pyproject.toml dependencies
- README.md: HF Space front matter (sdk=docker, app_port=7700)
- Source: server/, agentpub/, deploy/, docs/

Sampson 7-day observation period — HF Spaces PRIMARY for MVP.
Budget: \$0.10/day (sampson decision, not KAI's earlier \$1/day estimate)." 2>&1 | tail -5
fi

# 4. Pull first (HF Space has its own initial commit), then push via one-shot URL
echo ""
echo "[4/5] Pulling HF Space initial commit + pushing (one-shot URL, no token in .git/config)..."
# Add HF remote temporarily (without token — use env var or placeholder)
git remote add hf "https://huggingface.co/spaces/sampson119/agentpub" 2>/dev/null || git remote set-url hf "https://huggingface.co/spaces/sampson119/agentpub"
# Pull (with token) — allows non-fast-forward merge of HF's initial commit
git pull --no-edit --rebase=false --allow-unrelated-histories "https://sampson119:${HF_TOKEN}@huggingface.co/spaces/sampson119/agentpub" main 2>&1 | tail -5 || echo "  (pull had conflicts — manual resolution may be needed)"
# Push with token in URL (one-shot, not stored)
git push "https://sampson119:${HF_TOKEN}@huggingface.co/spaces/sampson119/agentpub" main 2>&1 | tail -10
# Remove remote to avoid token confusion later
git remote remove hf 2>/dev/null || true

# 5. Wait + report
echo ""
echo "[5/5] HF Space build status..."
echo "  Build typically takes 30-90s. Check:"
echo "    https://huggingface.co/spaces/sampson119/agentpub"
echo ""
echo "Once 'Running' status shows, verify:"
echo "    curl -fsSL https://sampson119-agentpub.hf.space/ | jq -e '.status == \"ok\"'"
echo "    curl -fsSL https://sampson119-agentpub.hf.space/llms.txt | head -3"
