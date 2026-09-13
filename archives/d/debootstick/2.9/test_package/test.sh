#!/bin/sh
# test_package/test.sh -- consumer smoke test for the packaged debootstick.
# Called by conanfile.py test() with DEBOOTSTICK_BIN pointing at the package
# binary and DBSTCK_PKG at the package folder.
# POSIX sh only (HMBS shell=/bin/sh; toybox ash rejects pipefail).
# Every scenario asserts real script behavior; any failure exits non-zero.
set -eu

DEBOOTSTICK_BIN="${DEBOOTSTICK_BIN:-debootstick}"
DBSTCK_PKG="${DBSTCK_PKG:-}"
# Installed launcher is OHOS-portable (recipe stamps @VERSION@ and swaps
# ${BASH_SOURCE[0]} for $0); the --version/--help/negative CLI paths exit
# before the `with` DSL lines, so they run under bash or POSIX sh.
# Prefer bash when present, else fall back to HMBS SHELL=/bin/sh.
BASH_BIN=""
for _c in /data/service/hnp/bin/bash /bin/bash; do
    if [ -x "$_c" ]; then BASH_BIN="$_c"; break; fi
done
if [ -z "$BASH_BIN" ] && command -v bash >/dev/null 2>&1; then BASH_BIN="bash"; fi
if [ -z "$BASH_BIN" ]; then
    if [ -n "${CONFIG_SHELL:-}" ]; then BASH_BIN="$CONFIG_SHELL"
    elif [ -n "${SHELL:-}" ]; then BASH_BIN="$SHELL"
    else BASH_BIN="sh"
    fi
fi
command -v "$BASH_BIN" >/dev/null 2>&1 || BASH_BIN="sh"

echo "[HMBS tmp] TMPDIR=${TMPDIR:-} HMBS_TMPDIR=${HMBS_TMPDIR:-}"
# HMBS [readonly_tmp]: /tmp is erofs read-only on device. Honor the injected
# writable dir so any child mktemp/command-substitution temp files avoid /tmp.
# No /tmp is hardcoded below; this only sanitizes the env for children.
if [ -z "${TMPDIR:-}" ] || [ ! -d "${TMPDIR:-}" ] || [ ! -w "${TMPDIR:-}" ] || [ "${TMPDIR:-}" = "/tmp" ]; then
    for _d in "${HMBS_TMPDIR:-}" "${TMP:-}" "${TEMP:-}" "${HOME:-}/tmp" ./hmbs-tmp; do
        if [ -n "$_d" ] && [ -d "$_d" ] && [ -w "$_d" ]; then
            TMPDIR="$_d"; break
        fi
    done
    if [ ! -d "${TMPDIR:-}" ]; then
        mkdir -p ./hmbs-tmp 2>/dev/null || true
        [ -d ./hmbs-tmp ] && TMPDIR="./hmbs-tmp"
    fi
fi
export TMPDIR
TMP="${TMP:-$TMPDIR}"; TEMP="${TEMP:-$TMPDIR}"; export TMP TEMP
echo "[HMBS tmp] effective TMPDIR=$TMPDIR"

discovered=6
passed=0

fail() { echo "FAIL: $*"; exit 1; }
pass() { echo "PASS: $*"; }

emit_marker() {
    # $1=true|false $2=passedCount
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"test.sh","discovered":%d,"passedCount":%d}\n' \
        "$1" "$discovered" "$2"
}

[ -f "$DEBOOTSTICK_BIN" ] || { emit_marker false 0; fail "launcher not found: $DEBOOTSTICK_BIN"; }
[ -r "$DEBOOTSTICK_BIN" ] || { emit_marker false 0; fail "launcher not readable: $DEBOOTSTICK_BIN"; }
if [ ! -x "$DEBOOTSTICK_BIN" ]; then
    echo "WARN: launcher missing +x bit (HMDFS ignores chmod); continuing via interpreter $BASH_BIN"
else
    echo "PASS: launcher installed and executable"
fi

# 1) --version prints the exact stamped version (falsifiable: unstamped
#    @VERSION@ or a wrong version fails here instead of passing silently).
out=$("$BASH_BIN" "$DEBOOTSTICK_BIN" --version 2>&1)
rc=$?
[ $rc -eq 0 ] || { emit_marker false "$passed"; fail "--version exited $rc: $out"; }
[ "$out" = "debootstick 2.9" ] || { emit_marker false "$passed"; fail "--version mismatch: got '$out'"; }
pass "--version reports debootstick 2.9"
passed=$((passed + 1))

# 2) --help exits 0 and shows usage.
out=$("$BASH_BIN" "$DEBOOTSTICK_BIN" --help 2>&1)
rc=$?
[ $rc -eq 0 ] || { emit_marker false "$passed"; fail "--help exited $rc: $out"; }
case "$out" in
    *[Uu]sage*) pass "--help shows usage" ;;
    *) emit_marker false "$passed"; fail "--help shows no usage text: $out" ;;
esac
passed=$((passed + 1))

# 3) --help-os-support exercises the os-detect helper.
out=$("$BASH_BIN" "$DEBOOTSTICK_BIN" --help-os-support 2>&1)
rc=$?
[ $rc -eq 0 ] || { emit_marker false "$passed"; fail "--help-os-support exited $rc: $out"; }
[ -n "$out" ] || { emit_marker false "$passed"; fail "--help-os-support printed nothing"; }
pass "--help-os-support describes OS support"
passed=$((passed + 1))

# 4) Unknown option must fail closed (negative path).
# NOTE: guarded with set +e: toybox sh aborts on `var=$(failing-cmd)` under
# `set -e` before `rc=$?` runs; without the guard the script exits 1 here
# with no HMBS_TEST_PACKAGE_RESULT marker (observed preflight failure after
# the 3rd PASS). Only the capture is unguarded, asserts stay under set -e.
set +e
out=$("$BASH_BIN" "$DEBOOTSTICK_BIN" --no-such-option 2>&1)
rc=$?
set -e
[ $rc -ne 0 ] || { emit_marker false "$passed"; fail "unknown option unexpectedly exited 0: $out"; }
pass "unknown option exits non-zero"
passed=$((passed + 1))

# 5) Missing positional args must fail closed with usage.
set +e
out=$("$BASH_BIN" "$DEBOOTSTICK_BIN" --config-root-password-none 2>&1)
rc=$?
set -e
[ $rc -ne 0 ] || { emit_marker false "$passed"; fail "missing-args unexpectedly exited 0: $out"; }
pass "missing chroot/image args exit non-zero"
passed=$((passed + 1))

# 6) Data payload installed (sourced helpers + disk layouts).
for rel in "scripts/create-image/cmdline" \
           "scripts/create-image/os-detect" \
           "disk-layouts"; do
    found=0
    for base in "$DBSTCK_PKG/bin" "$DBSTCK_PKG/share/debootstick" \
                "$DBSTCK_PKG/usr/share/debootstick"; do
        if [ -e "$base/$rel" ]; then found=1; break; fi
    done
    [ $found -eq 1 ] || { emit_marker false "$passed"; fail "data file missing: $rel (looked under bin/, share/debootstick/)"; }
done
pass "scripts + disk-layouts data files present"
passed=$((passed + 1))

if [ "$passed" -ne "$discovered" ]; then
    echo "FAIL: $((discovered - passed))/$discovered checks failed"
    emit_marker false "$passed"
    exit 1
fi

echo "[test] All debootstick consumer tests passed ($passed/$discovered scenarios)"
emit_marker true "$passed"
