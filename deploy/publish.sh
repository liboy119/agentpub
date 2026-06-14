#!/bin/bash
# AgentPub one-shot publish script
# ----------------------------------------------------------------------
# Get tokens (free PyPI account required):
#   TestPyPI: https://test.pypi.org/manage/account/token/  (scope: "project: agentpub"  or "Entire account")
#   PyPI:     https://pypi.org/manage/account/token/
#
# Usage:
#   export TWINE_TESTPASSWORD='pypi-XXXX...'
#   export TWINE_PASSWORD='pypi-XXXX...'
#   ./publish.sh testpypi   # uploads to test.pypi.org
#   ./publish.sh pypi       # uploads to pypi.org (production)
#
# DO NOT commit tokens to git. Use GitHub Actions trusted publishing
# for CI (see .github/workflows/publish.yml).
# ----------------------------------------------------------------------

set -e
cd "$(dirname "$0")/.."

if [ -z "$TWINE_TESTPASSWORD" ] && [ -z "$TWINE_PASSWORD" ]; then
    echo "ERROR: no PyPI token in env."
    echo "  export TWINE_TESTPASSWORD='pypi-...'"
    echo "  export TWINE_PASSWORD='pypi-...'"
    exit 1
fi

echo "============================================================"
echo "  AgentPub Publish"
echo "============================================================"

# 1. Build
echo ""
echo "[1/4] Building sdist + wheel..."
source .venv/bin/activate
python -m build --sdist --wheel 2>&1 | tail -5
ls -la dist/
echo "OK build"

# 2. Verify metadata
echo ""
echo "[2/4] twine check ..."
twine check dist/* 2>&1 | tail -5

# 3. Decide target
TARGET="${1:-testpypi}"
case "$TARGET" in
    testpypi)
        if [ -z "$TWINE_TESTPASSWORD" ]; then
            echo "ERROR: TWINE_TESTPASSWORD not set"
            exit 1
        fi
        REPO_FLAG="--repository testpypi"
        REPO_URL="https://test.pypi.org/"
        ;;
    pypi)
        if [ -z "$TWINE_PASSWORD" ]; then
            echo "ERROR: TWINE_PASSWORD not set"
            exit 1
        fi
        REPO_FLAG=""
        REPO_URL="https://pypi.org/"
        ;;
    *)
        echo "ERROR: unknown target '$TARGET'  (use 'testpypi' or 'pypi')"
        exit 1
        ;;
esac

# 4. Upload
echo ""
echo "[3/4] Uploading to $REPO_URL ..."
TWINE_USERNAME=__token__ twine upload $REPO_FLAG dist/* 2>&1 | tail -15

echo ""
echo "============================================================"
echo "  Done. $REPO_URL"
echo "============================================================"

# 5. Verify
if [ "$TARGET" = "testpypi" ]; then
    echo ""
    echo "[4/4] Verify install (in a fresh venv):"
    echo "   pip install -i https://test.pypi.org/simple/ agentpub"
fi
