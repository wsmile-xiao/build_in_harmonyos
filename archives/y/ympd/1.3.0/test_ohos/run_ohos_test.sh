#!/usr/bin/zsh
# HarmonyOS PC validation for the packaged ympd 1.3.0 executable.
# Run on the target device: zsh run_ohos_test.sh <path-to-ympd> [smoke_test.py] [conanrun.sh]
set -euo pipefail

BIN="${1:-}"
SCRIPT="${2:-$(dirname "$0")/../test_package/smoke_test.py}"
RUN_ENV="${3:-}"

[ -n "$BIN" ] && [ -x "$BIN" ] || {
    echo "        [fail] usage: $0 <executable-ympd> [smoke_test.py]"
    exit 2
}
[ -f "$SCRIPT" ] || { echo "        [fail] smoke test not found: $SCRIPT"; exit 2; }
if [ -n "$RUN_ENV" ]; then
    [ -f "$RUN_ENV" ] || { echo "        [fail] Conan run environment not found: $RUN_ENV"; exit 2; }
    . "$RUN_ENV"
fi

HEADER=$(readelf -h "$BIN")
echo "[step] Verify HarmonyOS executable architecture"
echo "$HEADER" | grep -q 'Class:.*ELF64' || {
    echo "        [fail] package is not ELF64"
    exit 1
}
echo "$HEADER" | grep -q 'Machine:.*AArch64' || {
    echo "        [fail] package is not AArch64"
    exit 1
}
echo "        [ok] HarmonyOS package is ELF64 AArch64"

python3 "$SCRIPT" "$BIN"
