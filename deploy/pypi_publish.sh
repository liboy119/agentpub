#!/bin/bash
# AgentPub - PyPI 发布命令模板
# 前置: sampson 有 PyPI 账号 + API token
# 流程:
#   1. 注册 PyPI: https://pypi.org/account/register/
#   2. 创建 API token: https://pypi.org/manage/account/token/
#   3. 把 token 配到 ~/.pypirc (见下)
#   4. 跑这个脚本
set -e

cd /home/kali/桌面/agent/agentpub

echo "=== 1. 检查 ~/.pypirc ==="
if [ ! -f ~/.pypirc ]; then
    echo "  ❌ ~/.pypirc 不存在, 创建模板:"
    cat > ~/.pypirc << 'EOF'
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-XXXXXXXXXXXXXXXXXXXXXXXXXXXX   # 替换为你的 token

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-XXXXXXXXXXXXXXXXXXXXXXXXXXXX   # testpypi 的 token
EOF
    echo "  ✅ 模板已写到 ~/.pypirc"
    echo "  ⚠️  sampson 你需要把里面的 XXXX 换成真 token"
    exit 1
fi
echo "  ✅ ~/.pypirc 存在"

echo ""
echo "=== 2. 装 build 工具 ==="
pip install --quiet --break-system-packages build twine 2>&1 | tail -3

echo ""
echo "=== 3. 清理 + 重新打包 ==="
rm -rf dist/ build/ agentpub.egg-info/
python3 -m build
echo "  ✅ dist/ 生成:"
ls -la dist/

echo ""
echo "=== 4. (推荐) 先发到 TestPyPI 测一遍 ==="
echo "  python3 -m twine upload --repository testpypi dist/*"
echo "  → 看 https://test.pypi.org/project/agentpub/"
echo ""
echo "  测安装: pip install -i https://test.pypi.org/simple/ agentpub"

echo ""
echo "=== 5. 正式发到 PyPI ==="
echo "  python3 -m twine upload dist/*"
echo "  → 看 https://pypi.org/project/agentpub/"
echo ""
echo "  任何人可以装: pip install agentpub"

echo ""
echo "=== 6. 后续版本更新 ==="
echo "  1. 改 pyproject.toml 的 version 字段 (0.1.0 → 0.1.1)"
echo "  2. git tag v0.1.1 && git push --tags"
echo "  3. 重新跑这个脚本"
