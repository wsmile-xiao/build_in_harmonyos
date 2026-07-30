#!/usr/bin/env sh
# zinit test_package smoke test
# Verify the zinit scripts are installed and usable from a consumer package.

set -eu

if (set -o pipefail) 2>/dev/null; then
    set -o pipefail
fi

echo "=== zinit 3.15.0 test_package smoke test ==="

ZINIT_DIR="${CONAN_PACKAGE_FOLDER_zinit:-}/share/zinit"

if [ -z "${CONAN_PACKAGE_FOLDER_zinit:-}" ] || [ ! -d "$ZINIT_DIR" ]; then
    echo "ERROR: CONAN_PACKAGE_FOLDER_zinit not set or zinit package directory missing"
    exit 1
fi

echo "zinit dir: $ZINIT_DIR"

for f in zinit.zsh zinit-autoload.zsh zinit-install.zsh VERSION; do
    if [ -f "$ZINIT_DIR/$f" ]; then
        echo "[ok] Found $f"
    else
        echo "[fail] Missing $f"
        exit 1
    fi
done

VERSION=$(cat "$ZINIT_DIR/VERSION")
if [ "$VERSION" = "3.15.0" ]; then
    echo "[ok] VERSION matches 3.15.0"
else
    echo "[fail] VERSION mismatch: $VERSION"
    exit 1
fi

if [ -x "$ZINIT_DIR/zinit.zsh" ]; then
    echo "[ok] zinit.zsh is executable"
else
    echo "[fail] zinit.zsh is not executable"
    exit 1
fi

if command -v zsh >/dev/null 2>&1; then
    zsh -n "$ZINIT_DIR/zinit.zsh"
    zsh -n "$ZINIT_DIR/zinit-autoload.zsh"
    zsh -n "$ZINIT_DIR/zinit-install.zsh"
    zsh -fc ". '$ZINIT_DIR/zinit.zsh'; typeset -f zinit >/dev/null"
    echo "[ok] zinit sources and defines zinit function"
else
    grep -q "^[[:space:]]*zinit()" "$ZINIT_DIR/zinit.zsh"
    echo "[ok] zinit function definition present; zsh not available for runtime source check"
fi

echo "=== All checks passed ==="
