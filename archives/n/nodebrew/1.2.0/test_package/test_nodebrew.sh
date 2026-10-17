#!/usr/bin/env bash
# nodebrew 1.2.0 — consumer smoke test (real execution, same checks as
# conanfile.py test()).  nodebrew is a pure perl script tool.
# Usage: bash test_nodebrew.sh <absolute-path-to-package-bin-dir>
set -uo pipefail

BIN_DIR="${1:-}"
if [ -z "$BIN_DIR" ]; then
    echo "usage: bash test_nodebrew.sh <package bin dir>" >&2
    exit 2
fi

PERL="${PERL:-perl}"
NB="$BIN_DIR/nodebrew"
FAIL=0

# ── 1. bin/nodebrew exists ──
if [ ! -e "$NB" ]; then
    echo "[fail] nodebrew missing in $BIN_DIR"
    FAIL=1
fi

# ── 2. bin/nodebrew is executable ──
if [ -e "$NB" ] && [ ! -x "$NB" ]; then
    echo "[fail] nodebrew is not executable"
    FAIL=1
fi

# ── 3. shebang is perl + perl -c syntax check ──
if [ -f "$NB" ]; then
    SHEBANG=$(head -1 "$NB")
    if [[ "$SHEBANG" != *perl* ]]; then
        echo "[fail] unexpected shebang: $SHEBANG"
        FAIL=1
    fi
    if ! "$PERL" -c "$NB" >/dev/null 2>&1; then
        echo "[fail] perl -c syntax check failed for $NB"
        FAIL=1
    fi
else
    echo "[fail] nodebrew is not a regular file"
    FAIL=1
fi

# ── 4. `nodebrew version` reports 1.2.0 ──
if out=$("$PERL" "$NB" version 2>&1); then
    if ! echo "$out" | grep -q "1\.2\.0"; then
        echo "[fail] 'nodebrew version' output missing 1.2.0"
        FAIL=1
    fi
else
    echo "[fail] 'perl nodebrew version' exited non-zero"
    FAIL=1
fi

# ── 5. `nodebrew help` prints the versioned header ──
if out=$("$PERL" "$NB" help 2>&1); then
    if ! echo "$out" | grep -q "nodebrew 1.2.0"; then
        echo "[fail] 'nodebrew help' header missing 'nodebrew 1.2.0'"
        FAIL=1
    fi
else
    echo "[fail] 'perl nodebrew help' exited non-zero"
    FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
    echo "[ok] nodebrew smoke test: OK"
fi
exit "$FAIL"
