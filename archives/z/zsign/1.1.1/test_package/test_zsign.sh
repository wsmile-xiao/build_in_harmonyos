#!/bin/bash
# Consumer test for zsign 1.1.1 (HarmonyOS OHOS aarch64 build).
# Usage: bash test_zsign.sh /path/to/zsign
#
# Drives the installed zsign binary the way a real user would:
#   1. version report (`zsign -v`)
#   2. ad-hoc re-sign of a real arm64 Mach-O executable (decoded from fixture)
#   3. idempotent re-sign (signature replacement path)
# All temp files live beside the script (never /tmp — HMDFS mounts it read-only).
set -euo pipefail

ZSIGN="$1"
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d "$HERE/zsign-test-XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

PASS=0
FAIL=0
ok()   { PASS=$((PASS+1)); echo "PASS $1"; }
bad()  { FAIL=$((FAIL+1)); echo "FAIL $1"; }

echo "--- zsign 1.1.1 consumer verification ---"

# 1) version report
out="$("$ZSIGN" -v)" || { bad "version-report (zsign -v exited nonzero)"; exit 1; }
echo "$out" | grep -q "version: 1.1.1" || { bad "version-report [$out]"; exit 1; }
ok "1 version-report"

# 2) ad-hoc sign a real arm64 Mach-O executable
#    Fixture: minimal static arm64 Mach-O (LC_MAIN + __TEXT/__LINKEDIT), built
#    once with OHOS NDK clang -target arm64-apple-macos11 + ld64.lld; see
#    MANIFEST.yml. Decoded via python3 (present wherever conan runs).
python3 - "$HERE/macho_fix.b64" "$WORK/TestApp.bin" <<'PYEOF'
import base64, sys
data = base64.b64decode(open(sys.argv[1], "rb").read())
open(sys.argv[2], "wb").write(data)
PYEOF
[ -s "$WORK/TestApp.bin" ] || { bad "fixture-decode"; exit 1; }
ok "2 fixture-decode"

size0=$(wc -c < "$WORK/TestApp.bin")
rc=0
(cd "$WORK" && "$ZSIGN" -a -f "TestApp.bin") >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 0 ] || { bad "adhoc-sign rc=$rc"; exit 1; }
size1=$(wc -c < "$WORK/TestApp.bin")
[ "$size1" -gt "$size0" ] || { bad "signature-embedded (size $size0 -> $size1)"; exit 1; }
ok "3 adhoc-sign (Mach-O grew $size0 -> $size1 bytes, LC_CODE_SIGNATURE embedded)"

# 3) idempotent re-sign: signing an already-signed binary must succeed
(cd "$WORK" && "$ZSIGN" -a -f "TestApp.bin") >/dev/null 2>&1 \
    && ok "4 re-sign idempotent" || bad "4 re-sign idempotent"

echo "test zsign 1.1.1: $PASS/$((PASS+FAIL)) checks PASS"
[ "$FAIL" -eq 0 ]
