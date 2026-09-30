#!/usr/bin/env bash
# Compile and run a C consumer against the installed package, never the build tree.
set -u

PKG_DIR="${1:-}"
WORK_DIR="${2:-}"
if [ -z "$PKG_DIR" ] || [ -z "$WORK_DIR" ]; then
    echo "usage: test.sh <package-folder> <work-dir>" >&2
    exit 2
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
INC_DIR="$PKG_DIR/include"
LIB_DIR="$PKG_DIR/lib"
CC="${CC:-clang}"

if ! command -v "$CC" >/dev/null 2>&1; then
    if [ -x /data/service/hnp/bin/clang ]; then
        CC=/data/service/hnp/bin/clang
    else
        echo "[fail] no C compiler available" >&2
        exit 2
    fi
fi

mkdir -p "$WORK_DIR"
consumer="$WORK_DIR/libconfig_consumer"
consumer_out="$WORK_DIR/consumer.out"
cc_log="$WORK_DIR/cc.log"
PASS=0
FAIL=0

check()
{
    label="$1"
    shift
    if "$@"; then
        PASS=$((PASS + 1))
        echo "  [ok]   $label"
    else
        FAIL=$((FAIL + 1))
        echo "  [fail] $label" >&2
    fi
}

check "C header include/libconfig.h installed" test -f "$INC_DIR/libconfig.h"
check "C++ header include/libconfig.h++ installed" test -f "$INC_DIR/libconfig.h++"
check "C static library lib/libconfig.a installed" test -f "$LIB_DIR/libconfig.a"
check "C++ static library lib/libconfig++.a installed" test -f "$LIB_DIR/libconfig++.a"
check "pkg-config file libconfig.pc installed" test -f "$LIB_DIR/pkgconfig/libconfig.pc"

rm -f "$consumer" "$consumer_out" "$cc_log"
if "$CC" -O2 -I"$INC_DIR" "$SCRIPT_DIR/test.c" \
    -L"$LIB_DIR" -lconfig -lm -o "$consumer" >"$cc_log" 2>&1; then
    PASS=$((PASS + 1))
    echo "  [ok]   consumer compiles and links against installed libconfig.a"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] consumer compile/link failed" >&2
    cat "$cc_log" >&2
fi

rc=127
if [ -x "$consumer" ]; then
    "$consumer" "$SCRIPT_DIR/consumer.cfg" >"$consumer_out" 2>&1
    rc=$?
fi
check "consumer exits successfully" test "$rc" -eq 0
check "consumer parses server.host=localhost server.port=8080 enabled=1" \
    grep -q '^server\.host=localhost server\.port=8080 enabled=1$' "$consumer_out"
check "consumer reports C API round-trip OK" \
    grep -q '^test libconfig 1\.7\.3 consumer: OK$' "$consumer_out"

echo "[test] libconfig consumer assertions: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
