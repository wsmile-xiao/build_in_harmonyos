#!/usr/bin/env bash
set -euo pipefail
SSLDUMP="${1:-ssldump}"
output="$("$SSLDUMP" -v 2>&1 || true)"
if echo "$output" | grep -qiE 'ssldump|version'; then
    echo "[ok] ssldump version output verified"
    exit 0
else
    echo "[fail] ssldump version output not found"
    exit 1
fi
