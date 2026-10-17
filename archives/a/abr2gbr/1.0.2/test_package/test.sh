#!/bin/bash
# test_package/test.sh — smoke test for abr2gbr
set -euo pipefail

echo "[test] abr2gbr --help"
rc=0
abr2gbr --help >/dev/null 2>&1 || rc=$?
if [ "$rc" -eq 0 ]; then
    echo "✅ abr2gbr --help OK (exit 0)"
elif [ "$rc" -eq 126 ] || [ "$rc" -eq 127 ]; then
    # 126 = not executable, 127 = command not found — package defect
    echo "❌ abr2gbr missing or not executable (exit $rc)"
    exit 1
elif [ "$rc" -ge 128 ]; then
    echo "❌ abr2gbr crashed (exit $rc)"
    exit 1
else
    echo "✅ abr2gbr --help OK (non-zero exit $rc expected)"
fi
