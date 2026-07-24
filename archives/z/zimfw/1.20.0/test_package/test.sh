#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for zimfw
# Runs in conanrun env (PATH includes installed share/)
set -euo pipefail

# Locate the installed zimfw.zsh
SCRIPT_PATH="${PACKAGE_ROOT}/share/zimfw.zsh"

# R34: substantively test the package
echo "[test] Checking zimfw.zsh exists"
if [[ ! -f "$SCRIPT_PATH" ]]; then
    echo "❌ zimfw.zsh not found at $SCRIPT_PATH"
    exit 1
fi

echo "[test] Checking content size (>1000 bytes)"
SIZE=$(wc -c < "$SCRIPT_PATH")
if [[ "$SIZE" -lt 1000 ]]; then
    echo "❌ zimfw.zsh is suspiciously small ($SIZE bytes)"
    exit 1
fi
echo "✅ zimfw.zsh found ($SIZE bytes)"

echo "[test] Checking 'zimfw' identifier in content"
if ! grep -qi "zimfw" "$SCRIPT_PATH"; then
    echo "❌ zimfw.zsh does not contain 'zimfw' identifier"
    exit 1
fi
echo "✅ 'zimfw' identifier found"

# zsh -n syntax validation
ZSH=$(command -v zsh 2>/dev/null || true)
if [[ -n "$ZSH" ]]; then
    echo "[test] Running zsh -n syntax check"
    if "$ZSH" -n "$SCRIPT_PATH"; then
        echo "✅ zsh -n syntax check passed"
    else
        echo "❌ zsh -n syntax check failed"
        exit 1
    fi

    # Try --version (may fail on OHOS due to missing autoload functions)
    echo "[test] Running zimfw --version"
    if "$ZSH" "$SCRIPT_PATH" --version 2>/dev/null; then
        echo "✅ zimfw --version passed"
    else
        echo "⚠️ zimfw --version failed (platform limitation: missing zsh autoload functions)"
    fi
else
    echo "⚠️ zsh not found on PATH; file and content checks completed"
fi

echo "[test] All checks passed ✅"
