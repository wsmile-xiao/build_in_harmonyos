#!/bin/sh
# aliki-0.3.0 packaged-tool smoke test.
#
# aliki is an X11 GUI tool and aliki-rt a real-time capture program: neither
# can run to completion headless on OHOS/CI, so the pass condition is that
# each binary loads its full runtime shared-library closure and reaches its
# normal early-exit path instead of dying in the dynamic loader.
#
#   aliki -h    prints the version banner ("Aliki-0.3.0 ...") to stderr and
#               exits 1 (upstream help() calls exit(1)) — the banner is the
#               assertion that the binary started and linked.
#   aliki-rt    with no shared-memory argument returns 1 (main() ac<2) —
#               exit 1 (not 127 loader error) proves the closure resolved.
#
# NOTE: OHOS /system/bin/sh (toybox) lacks command substitution `$(...)`,
# so the version check is done through a pipeline instead.
#
# Usage: test_aliki.sh <path-to-bin-dir>

set -u

BIN_DIR="$1"

if [ ! -x "$BIN_DIR/aliki" ] || [ ! -x "$BIN_DIR/aliki-rt" ]; then
    echo "FAIL: aliki/aliki-rt not found in $BIN_DIR" >&2
    exit 1
fi

# aliki -h must print the version banner (exit code 1 is expected upstream).
if ! "$BIN_DIR/aliki" -h 2>&1 | grep -q "Aliki-0.3.0"; then
    echo "FAIL: aliki -h did not print the version banner" >&2
    "$BIN_DIR/aliki" -h 2>&1 | head -n 5 >&2
    exit 1
fi

# aliki-rt with no argument must return 1 (missing shared-memory argument),
# not 127 (shared-library load failure) and not crash.
"$BIN_DIR/aliki-rt" >/dev/null 2>&1
rc=$?
if [ "$rc" -ne 1 ]; then
    echo "FAIL: aliki-rt returned $rc, expected 1" >&2
    exit 1
fi

echo "ALIKI_SMOKE_PASS banner=1 aliki-rt_exit=1"
exit 0
