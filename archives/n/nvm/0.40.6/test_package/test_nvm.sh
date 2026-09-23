#!/usr/bin/env bash
# R34: real smoke test for nvm 0.40.6 — exercises the packaged artifact.
# nvm is a shell script tool (sourced, not executed directly), so we verify:
# - nvm.sh presence, bash syntax
# - nvm-exec presence, executable bit, shebang
# - Source nvm.sh and call nvm --version
set -uo pipefail

BIN_DIR="${1:?usage: test_nvm.sh <package bin dir>}"

FAIL=0
NVM_SH="$BIN_DIR/nvm.sh"
NVM_EXEC="$BIN_DIR/nvm-exec"

# Check nvm.sh exists
if [ ! -e "$NVM_SH" ]; then
    echo "[fail] nvm.sh missing in $BIN_DIR"
    FAIL=1
fi

# Check nvm-exec exists and is executable
if [ ! -e "$NVM_EXEC" ]; then
    echo "[fail] nvm-exec missing in $BIN_DIR"
    FAIL=1
fi

# Check bash syntax of nvm.sh (it's a sourced function, no shebang needed)
if [ -f "$NVM_SH" ]; then
    if ! bash -n "$NVM_SH"; then
        echo "[fail] nvm.sh bash syntax check failed"
        FAIL=1
    fi
fi

# Check shebang of nvm-exec (it IS a standalone executable)
if [ -f "$NVM_EXEC" ]; then
    SHEBANG=$(head -1 "$NVM_EXEC")
    if [[ "$SHEBANG" != *bash* ]]; then
        echo "[fail] unexpected shebang in nvm-exec: $SHEBANG"
        FAIL=1
    fi
    if ! bash -n "$NVM_EXEC"; then
        echo "[fail] nvm-exec bash syntax check failed"
        FAIL=1
    fi
fi

# Source nvm.sh and verify nvm function is available, then check version
if [ "$FAIL" -eq 0 ]; then
    export NVM_DIR=$(mktemp -d 2>/dev/null || mktemp -d "$HOME/tmp/nvm-test-XXXXXX")
    # shellcheck source=/dev/null
    . "$NVM_SH" 2>/dev/null
    # nvm is a function, verify it exists
    if ! type nvm > /dev/null 2>&1; then
        echo "[fail] nvm function not available after sourcing nvm.sh"
        FAIL=1
    else
        # Check nvm --version output
        VER=$(nvm --version 2>/dev/null)
        if [ "$VER" != "0.40.6" ]; then
            echo "[fail] nvm --version output '$VER' != expected '0.40.6'"
            FAIL=1
        fi
    fi
    rm -rf "$NVM_DIR"
fi

if [ "$FAIL" -eq 0 ]; then
    echo "[ok] nvm smoke test: OK"
fi
exit "$FAIL"
