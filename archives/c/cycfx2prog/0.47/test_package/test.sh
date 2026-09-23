#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the cycfx2prog executable.
#
# Runs inside the conanrun environment, so PATH contains the installed bin/.
# No network, no hardware, no writes outside the current directory.
#
# Hardware vs. software split (established by reading the sources):
#   * HARDWARE path: -d=/-id= selection succeeds -> CypressFX2Device::open()
#     -> usb_set_configuration/usb_claim_interface -> the actual 8051 download
#     ("prg:"), reset/run, bulk/control endpoint traffic. Needs a real
#     EZ-USB FX2 device on the bus: not available in CI.
#   * SOFTWARE path (tested here): argument parsing, --help/--version/--list,
#     the libusb initialisation sequence and every "no such device" error
#     path. These run to completion on a machine with zero USB devices.
#
# Deliberately NOT `set -euo pipefail` (code-style §7): this script is an
# assertion *collector*, so it must survive a failing assertion and still reach
# the summary line with the full TOTAL/PASS/FAIL counts (the counts are what the
# L1e negative test compares). `set -e` would abort at the first failure and
# destroy the tally. A failing assertion still fails the run: `fail()` sets
# $FAILED and the script exits 1 at the bottom.
set -u

FAILED=0
FAIL_COUNT=0
ASSERT=0

pass() {
    ASSERT=$((ASSERT + 1))
    echo "OK  [$ASSERT] $1"
}

fail() {
    ASSERT=$((ASSERT + 1))
    FAIL_COUNT=$((FAIL_COUNT + 1))
    FAILED=1
    echo "FAIL[$ASSERT] $1"
}

expect_eq() {   # <actual> <expected> <description>
    if [ "$1" = "$2" ]; then
        pass "$3"
    else
        fail "$3 (got '$1', want '$2')"
    fi
}

expect_contains() {   # <haystack> <needle> <description>
    case "$1" in
        *"$2"*) pass "$3" ;;
        *)      fail "$3 (needle '$2' not found)" ;;
    esac
}

expect_not_contains() {   # <haystack> <needle> <description>
    case "$1" in
        *"$2"*) fail "$3 (unexpected '$2' present)" ;;
        *)      pass "$3" ;;
    esac
}

PROG=cycfx2prog

echo "=== [1] package layout: the tool is installed and executable"
PROG_PATH=$(command -v "$PROG" 2>/dev/null)
if [ -n "$PROG_PATH" ]; then
    pass "$PROG found in PATH via conanrun ($PROG_PATH)"
else
    fail "$PROG not found in PATH"
    echo "=== RESULT: FAIL ==="
    exit 1
fi

FILE_OUT=$(file "$PROG_PATH" 2>/dev/null)
echo "file: $FILE_OUT"
expect_contains "$FILE_OUT" "arm64" "$PROG is an AArch64 executable"
expect_contains "$FILE_OUT" "ld-musl-aarch64.so.1" "$PROG dynamically links the musl loader"

echo
echo "=== [2] --version: exact version string, no libusb involvement"
VER_OUT=$("$PROG" --version 2>&1)
VER_RC=$?
expect_eq "$VER_RC" "0" "--version exits 0"
# Guards the double-shell escaping of the -DCYCFX2PROG_VERSION macro: when the
# quoting is wrong the macro collapses to a floating point constant and glibc
# prints garbage instead of the version.
expect_eq "$VER_OUT" "cycfx2prog version 0.47" "--version prints the exact version line"

VER_OUT2=$("$PROG" --version 2>&1)
expect_eq "$VER_OUT2" "$VER_OUT" "--version output is deterministic across runs"

echo
echo "=== [3] --help: usage text and documented command set"
HELP_OUT=$("$PROG" --help 2>&1)
HELP_RC=$?
expect_eq "$HELP_RC" "0" "--help exits 0"
expect_contains "$HELP_OUT" "Usage: cycfx2prog [-d=BUS.DEV] [id=VV.PP[.N]] [commands...]" \
    "--help prints the upstream usage line"
expect_contains "$HELP_OUT" "--list" "--help documents --list"
expect_contains "$HELP_OUT" "-d=BBB.DDD" "--help documents the -d= device selector"
expect_contains "$HELP_OUT" "-id=VV.PP[.N]" "--help documents the -id= selector"
for CMD in reset run "prg:FILE" "delay:NN" "set:ADR,VAL" "dram:ADR,LEN" \
           "dbulk:EP,L[,N]" "sbulk:EP,STR" "fbulk:EP,FILE[,CS]" \
           "bench_bulk:EP,L[,CS]" "altif:[IF]" "ctrl:TYPE,REQUEST[,VALUE[,INDEX]]"; do
    expect_contains "$HELP_OUT" "$CMD" "--help documents command '$CMD'"
done

echo
echo "=== [4] --list: real libusb init/enumeration path through libusb-compat"
LIST_OUT=$("$PROG" --list 2>&1)
LIST_RC=$?
expect_eq "$LIST_RC" "0" "--list exits 0 (usb_init + usb_find_busses + usb_find_devices succeeded)"
expect_not_contains "$LIST_OUT" "usb_find_busses failed" "libusb bus enumeration did not fail"
expect_not_contains "$LIST_OUT" "usb_find_devices failed" "libusb device enumeration did not fail"

echo
echo "=== [5] dynamic linkage: the binary resolves the libusb-1.0 ABI at runtime"
NEEDED=$(readelf -dW "$PROG_PATH" 2>/dev/null)
expect_contains "$NEEDED" "libusb-1.0.so.0" "DT_NEEDED lists libusb-1.0.so.0 (libusb-compat -> libusb-1.0)"

echo
echo "=== [6] error paths: no device attached must fail cleanly with exit code 1"
NOARG_OUT=$("$PROG" 2>&1)
NOARG_RC=$?
expect_eq "$NOARG_RC" "1" "no-argument run exits 1"
expect_contains "$NOARG_OUT" "No unconfigured Cypress FX2 attached." \
    "no-argument run reports the missing default FX2 device"

ID_OUT=$("$PROG" -id=1234.5678 2>&1)
ID_RC=$?
expect_eq "$ID_RC" "1" "explicit -id= with no matching device exits 1"
expect_contains "$ID_OUT" "Device with vendorID=0x1234, productID=0x5678, nth=0 not attached." \
    "-id= reports the requested vendor/product/nth"

BAD_OUT=$("$PROG" --definitely-not-an-option 2>&1)
BAD_RC=$?
expect_eq "$BAD_RC" "1" "unknown option exits 1"
expect_contains "$BAD_OUT" 'Illegal option "--definitely-not-an-option".' \
    "unknown option is reported by name"

echo
if [ "$FAILED" -eq 0 ]; then
    echo "cycfx2prog test_package summary: TOTAL=$ASSERT PASS=$ASSERT FAIL=0"
    echo "=== RESULT: PASS ($ASSERT assertions, 0 failures) ==="
    exit 0
fi
echo "cycfx2prog test_package summary: TOTAL=$ASSERT PASS=$((ASSERT - FAIL_COUNT)) FAIL=$FAIL_COUNT"
echo "=== RESULT: FAIL ($ASSERT assertions, failures detected) ==="
exit 1
