#!/data/service/hnp/bin/bash
# test_package/test.sh — functional smoke test for vbackup scripts.
# Runs inside the conanrun env (PATH includes the installed bin/).
set -euo pipefail

# The packaged module scripts require bash (real bashisms upstream); the
# adaptation patches make them resolve bash via /usr/bin/env, so invoke the
# entry point through the same interpreter the harness knows.
VB="$(command -v vbackup)"
echo "[test] vbackup --version (via $VB)"
OUT="$(mktemp)"
bash "$VB" --version >"$OUT" 2>&1 || {
    echo "❌ vbackup --version exited non-zero"
    exit 1
}
grep -q "vbackup v1.0.1" "$OUT" || {
    echo "❌ vbackup --version did not report version 1.0.1"
    exit 1
}
rm -f "$OUT"
echo "✅ --version OK"

# Test 2: module framework loads (helpers resolvable through the relocatable
# prefix) — vbackup -l must print its usage without helper errors.
echo "[test] vbackup -l loads module framework"
if bash "$VB" -l 2>&1 | grep -q "No such file or directory"; then
    echo "❌ vbackup -l hit missing helper error"
    exit 1
fi
echo "✅ module framework OK"
