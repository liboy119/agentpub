#!/usr/bin/env bash
# AgentPub release script — one-shot: build + tag + push + GitHub release.
# Zero dependency on PyPI / MCP / 2FA / gh CLI.
#
# Pipeline (per sampson 6/15 plan):
#   1. python -m build --sdist --wheel
#   2. git tag v<version>  (idempotent: skip if exists, update if --force)
#   3. git push origin v<version>
#   4. GitHub release create v<version> with dist/* as assets
#      (via GitHub REST API, requires GH_TOKEN in env or ~/.netrc auth)
#
# Auth: needs a GitHub PAT with `repo` scope. Set one of:
#   export GH_TOKEN="ghp_..."           # preferred
#   export GITHUB_TOKEN="ghp_..."       # alt
#   or have credentials in ~/.netrc for github.com
#
# Usage:
#   ./deploy/release.sh                  # release current pyproject version
#   ./deploy/release.sh 0.1.3            # release specific version (overrides pyproject)
#   ./deploy/release.sh --force          # re-create tag if it already exists
#   ./deploy/release.sh --notes "msg"    # use custom release notes
#   ./deploy/release.sh --dry-run        # show what would happen, no side effects

set -euo pipefail

# ----- config -----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

# Detect owner/repo from git remote
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [[ "$REMOTE_URL" =~ github\.com[:/]([^/]+)/([^/.]+)(\.git)?$ ]]; then
    GH_OWNER="${BASH_REMATCH[1]}"
    GH_REPO="${BASH_REMATCH[2]}"
else
    echo "ERROR: cannot parse github owner/repo from origin: '$REMOTE_URL'" >&2
    exit 1
fi

# ----- args -----
VERSION_OVERRIDE=""
FORCE_TAG=0
NOTES_OVERRIDE=""
DRY_RUN=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --force) FORCE_TAG=1; shift ;;
        --notes) NOTES_OVERRIDE="$2"; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
        [0-9]*) VERSION_OVERRIDE="$1"; shift ;;
        *) echo "Unknown arg: $1" >&2; exit 1 ;;
    esac
done

# Read version from pyproject.toml (PEP 621 format)
VERSION=$(grep -E '^version\s*=\s*"[0-9]+\.[0-9]+\.[0-9]+"' pyproject.toml | head -1 | sed -E 's/.*"([0-9.]+)".*/\1/')
if [ -z "$VERSION" ] && [ -z "$VERSION_OVERRIDE" ]; then
    echo "ERROR: cannot find version in pyproject.toml and no override given" >&2
    exit 1
fi
VERSION="${VERSION_OVERRIDE:-$VERSION}"
TAG="v$VERSION"

echo "═══════════════════════════════════════════"
echo "  AgentPub release"
echo "═══════════════════════════════════════════"
echo "  Owner: $GH_OWNER / $GH_REPO"
echo "  Version: $VERSION  (tag: $TAG)"
echo "  Remote: $REMOTE_URL"
echo "  Mode:   $([ $DRY_RUN -eq 1 ] && echo 'DRY-RUN' || echo 'LIVE')"
echo ""

# ----- auth -----
if [ $DRY_RUN -eq 0 ]; then
    AUTH_TOKEN_VALUE=""
    if [ -n "${GH_TOKEN:-}" ]; then
        AUTH_TOKEN_VALUE="$GH_TOKEN"
    elif [ -n "${GITHUB_TOKEN:-}" ]; then
        AUTH_TOKEN_VALUE="$GITHUB_TOKEN"
    elif [ -f "$HOME/.netrc" ] && grep -q "github.com" "$HOME/.netrc"; then
        AUTH_TOKEN_VALUE=$(awk '/machine github.com/ {found=1; next} found && /password/ {print $2; exit}' "$HOME/.netrc")
    fi

    if [ -z "$AUTH_TOKEN_VALUE" ]; then
        echo "ERROR: no GitHub credentials found." >&2
        echo "  Set one of:" >&2
        echo "    export GH_TOKEN='ghp_...'" >&2
        echo "    export GITHUB_TOKEN='ghp_...'" >&2
        echo "    or add to ~/.netrc: machine github.com login <user> password <token>" >&2
        exit 1
    fi
    echo "✅ GitHub credentials loaded"
    AUTH_HEADER="token $AUTH_TOKEN_VALUE"
fi

# ----- 1. build -----
echo "→ [1/5] Building sdist + wheel..."
if [ $DRY_RUN -eq 1 ]; then
    echo "  (dry-run: would run: python -m build --sdist --wheel)"
else
    if [ -d .venv ]; then
        source .venv/bin/activate
    fi
    python -m build --sdist --wheel 2>&1 | tail -3
    ls -la dist/*.{whl,tar.gz} 2>/dev/null
fi

# ----- 2. tag -----
echo ""
echo "→ [2/5] Tagging $TAG..."
if git rev-parse "$TAG" >/dev/null 2>&1; then
    if [ $FORCE_TAG -eq 1 ]; then
        echo "  Tag exists, --force: deleting + re-creating"
        if [ $DRY_RUN -eq 0 ]; then
            git tag -d "$TAG"
            git push origin ":$TAG" 2>/dev/null || true
        fi
    else
        echo "  Tag $TAG already exists. Use --force to recreate, or bump version."
        exit 1
    fi
fi
if [ $DRY_RUN -eq 1 ]; then
    echo "  (dry-run: would run: git tag $TAG && git push origin $TAG)"
else
    git tag "$TAG"
    echo "  ✅ tag $TAG created locally"
fi

# ----- 3. push tag -----
echo ""
echo "→ [3/5] Pushing tag $TAG..."
if [ $DRY_RUN -eq 1 ]; then
    echo "  (dry-run: would run: git push origin $TAG)"
else
    git push origin "$TAG"
    echo "  ✅ tag pushed to origin"
fi

# ----- 4. GitHub release create -----
echo ""
echo "→ [4/5] Creating GitHub release $TAG..."

# Build notes (priority: --notes flag > CHANGELOG.md section > auto-generate)
if [ -n "$NOTES_OVERRIDE" ]; then
    NOTES="$NOTES_OVERRIDE"
elif [ -f CHANGELOG.md ] && grep -A 20 "^## \[$VERSION\]\|^## v$VERSION" CHANGELOG.md >/dev/null 2>&1; then
    NOTES=$(awk "/^## \[?$VERSION\]?/,/^## \[?$NEXT_VERSION\]?|^$/" CHANGELOG.md | head -30)
else
    NOTES="Release $VERSION. See commits: https://github.com/$GH_OWNER/$GH_REPO/compare/$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || echo "main")...$TAG"
fi

# JSON payload
PAYLOAD=$(python3 -c "
import json, sys
notes = sys.argv[1]
tag = sys.argv[2]
print(json.dumps({
    'tag_name': tag,
    'name': tag,
    'body': notes,
    'draft': False,
    'prerelease': False,
    'generate_release_notes': False,
}))
" "$NOTES" "$TAG")

if [ $DRY_RUN -eq 1 ]; then
    echo "  (dry-run: would POST to https://api.github.com/repos/$GH_OWNER/$GH_REPO/releases)"
    echo "  payload preview:"
    echo "$PAYLOAD" | head -5
else
    CREATE_RESP=$(curl -sS -X POST \
        -H "Authorization: $AUTH_HEADER" \
        -H "Accept: application/vnd.github+json" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        "https://api.github.com/repos/$GH_OWNER/$GH_REPO/releases")
    RELEASE_ID=$(echo "$CREATE_RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null)
    UPLOAD_URL=$(echo "$CREATE_RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('upload_url',''))" 2>/dev/null)
    HTML_URL=$(echo "$CREATE_RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('html_url',''))" 2>/dev/null)
    if [ -z "$RELEASE_ID" ]; then
        echo "  ❌ release create failed: $CREATE_RESP" | head -5
        exit 1
    fi
    echo "  ✅ release created: $HTML_URL"
fi

# ----- 5. upload dist assets -----
echo ""
echo "→ [5/5] Uploading dist/* to release..."
ASSETS=$(ls dist/agentpub_chat-${VERSION}-py3-none-any.whl dist/agentpub_chat-${VERSION}.tar.gz 2>/dev/null)
if [ -z "$ASSETS" ]; then
    echo "  ⚠️  no dist artifacts for version $VERSION found, skipping upload"
else
    for f in $ASSETS; do
        ASSET_NAME=$(basename "$f")
        SIZE=$(stat -c%s "$f")
        if [ $DRY_RUN -eq 1 ]; then
            echo "  (dry-run: would upload $ASSET_NAME ($SIZE bytes))"
        else
            echo "  uploading $ASSET_NAME ($SIZE bytes)..."
            # upload_url has {?name,label} template
            UPLOAD_URL_CLEAN=$(echo "$UPLOAD_URL" | sed 's/{?.*//')
            UPLOAD_RESP=$(curl -sS -X POST \
                -H "Authorization: $AUTH_HEADER" \
                -H "Content-Type: application/octet-stream" \
                --data-binary "@$f" \
                "${UPLOAD_URL_CLEAN}?name=$ASSET_NAME")
            UPLOADED_URL=$(echo "$UPLOAD_RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('browser_download_url',''))" 2>/dev/null)
            if [ -n "$UPLOADED_URL" ]; then
                echo "    ✅ $UPLOADED_URL"
            else
                echo "    ❌ upload failed: $(echo "$UPLOAD_RESP" | head -c 200)"
            fi
        fi
    done
fi

echo ""
echo "═══════════════════════════════════════════"
echo "  ✅ Release $TAG done"
echo "═══════════════════════════════════════════"
echo "  Release URL: https://github.com/$GH_OWNER/$GH_REPO/releases/tag/$TAG"
echo "  Install:     pip install https://github.com/$GH_OWNER/$GH_REPO/archive/refs/tags/$TAG.tar.gz"
echo "  Or:          pip install git+https://github.com/$GH_OWNER/$GH_REPO.git@$TAG"
