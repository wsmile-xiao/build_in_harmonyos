#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the aa3d executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -eu

echo "[test] aa3d --version"
aa3d --version | grep -q "aa3d 1.0"
echo "OK: --version returns aa3d 1.0"

echo "[test] aa3d functional (depth map -> stereogram)"
OUTPUT=$(printf '22222222222222222222\n22222222222222222222\n' | aa3d -w 40 -d) || exit 1
echo "$OUTPUT" | head -2
if [ -z "$OUTPUT" ]; then
    echo "FAIL: aa3d produced no output"
    exit 1
fi
echo "OK: produced $(echo "$OUTPUT" | wc -l) line(s) of stereogram output"
