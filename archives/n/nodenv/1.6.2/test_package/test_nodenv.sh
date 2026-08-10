#!/usr/bin/env bash
# R34: real smoke test for nodenv 1.6.2 — exercises the packaged artifact.
# nodenv is a bash script tool, so we verify presence, executable bit,
# shebang, bash syntax, and --version output.
set -uo pipefail

BIN_DIR="${1:?usage: test_nodenv.sh <package bin dir>}"

FAIL=0
NODENV="$BIN_DIR/nodenv"

# Check nodenv exists and is executable
if [ ! -e "$NODENV" ]; then
    echo "[fail] nodenv missing in $BIN_DIR"
    FAIL=1
fi

# Check shebang (nodenv is a symlink, follow it to read the actual script)
if [ -f "$NODENV" ]; then
    SHEBANG=$(head -1 "$NODENV")
    if [[ "$SHEBANG" != *bash* ]]; then
        echo "[fail] unexpected shebang: $SHEBANG"
        FAIL=1
    fi
    # Bash syntax check on the resolved file
    REAL_PATH=$(readlink -f "$NODENV" 2>/dev/null || echo "$NODENV")
    if ! bash -n "$REAL_PATH"; then
        echo "[fail] nodenv bash syntax check failed"
        FAIL=1
    fi
fi

# Run nodenv --version
if ! "$NODENV" --version 2>/dev/null | grep -q "1.6.2"; then
    echo "[fail] nodenv --version did not output expected version"
    FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
    echo "[ok] nodenv smoke test: OK"
fi
exit "$FAIL"
