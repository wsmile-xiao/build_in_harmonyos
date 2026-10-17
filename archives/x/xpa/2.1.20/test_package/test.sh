#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer functional test for libxpa.
# Starts the packaged xpans nameserver, then runs xpa_consumer which
# registers an access point and drives XPAGet/XPASet through it.
# The packaged bin dir is handed over explicitly by test_package/
# conanfile.py (PATH via the run env is a nice-to-have, not required).
if [ $# -ge 1 ] && [ -n "$1" ]; then
    PATH="$1:$PATH"
    export PATH
fi
set -euo pipefail

cd "$(dirname "$0")"

# /tmp is read-only on OHOS — use $HOME/tmp scratch
SCRATCH="${TMPDIR:-$HOME/tmp}/xpa-test-$$"
mkdir -p "$SCRATCH"
trap 'rm -rf "$SCRATCH"' EXIT

# locate the packaged binaries (explicit bin dir first, PATH as fallback)
XPANS=""
if [ -n "${1:-}" ] && [ -x "$1/xpans" ]; then
    XPANS="$1/xpans"
elif command -v xpans >/dev/null 2>&1; then
    XPANS="$(command -v xpans)"
fi
[ -n "$XPANS" ] || {
    echo "FAIL: xpans not found (bin dir or PATH)"
    exit 1
}

# locate the consumer binary (cmake_layout: build/<preset>/xpa_consumer)
CONSUMER=""
for c in ./xpa_consumer ./build/xpa_consumer ./build/*/xpa_consumer ./build/Release/xpa_consumer; do
    [ -x "$c" ] && CONSUMER="$c" && break
done
[ -n "$CONSUMER" ] || CONSUMER=$(find . -name xpa_consumer -type f 2>/dev/null | head -1)
[ -n "$CONSUMER" ] || {
    echo "FAIL: xpa_consumer binary not found"
    exit 1
}

echo "[test] start xpans nameserver"
"$XPANS" > "$SCRATCH/xpans.log" 2>&1 &
NSPID=$!
sleep 2
kill -0 "$NSPID" || {
    echo "FAIL: xpans not running"
    cat "$SCRATCH/xpans.log"
    exit 1
}
echo "OK: xpans up (pid $NSPID)"

# XPA_NS_HOST/PORT default to localhost:28561 (upstream default)
set +e
"$CONSUMER" > "$SCRATCH/consumer.log" 2>&1
RC=$?
set -e
kill "$NSPID" 2>/dev/null || true
wait "$NSPID" 2>/dev/null || true
cat "$SCRATCH/consumer.log"

[ "$RC" -eq 0 ] || {
    echo "FAIL: xpa_consumer exited $RC"
    exit 1
}
grep -q "ALL CONSUMER TESTS PASSED" "$SCRATCH/consumer.log" || {
    echo "FAIL: missing ALL CONSUMER TESTS PASSED marker"
    exit 1
}
echo "ALL CONSUMER TESTS PASSED (wrapper)"
