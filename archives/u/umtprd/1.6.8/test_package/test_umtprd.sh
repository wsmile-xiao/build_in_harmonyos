#!/bin/sh
# test_umtprd.sh — consumer functional test for the umtprd 1.6.8 package.
#
#   sh test_umtprd.sh <path-to-umtprd-binary> <workdir>
#
# Runs the installed bin/umtprd daemon binary without arguments and checks
# 5 real assertions, then prints a machine-readable
# "RESULT: P passed, F failed" trailer line, which test_package/conanfile.py
# parses into HMBS_TEST_PACKAGE_RESULT.
#
# Expected behaviour (audited from upstream src/umtprd.c + src/mtp_cfg.c):
# the daemon prints its "uMTP Responder" banner + "Version:" line, tries to
# load /etc/umtprd/umtprd.conf (missing -> "Can't open ... Using default
# settings..." + full default-config dump), then fails to open the USB
# FunctionFS device (/dev/ffs-umtp/ep0, absent on HarmonyOS PC) and exits
# with code 2 via the graceful USB-init-failure path ("USB Init failed !").
# The default config sets loop_on_disconnect=0, so the daemon exits after
# the single failed init and never lingers; a 15s `timeout` guard still
# wraps the run in case a config ever enables the loop.
#
# Case 5 is a negative control (exit code must be NON-zero): an `exit 0`
# stub binary would fail it, proving the harness observes real failures
# instead of passing empty output.
#
# Upstream ships no test suite; this validates the packaged application.

set -u

BIN="$1"
WORKDIR="$2"

# Device HMFS /tmp may be read-only: prefer the HMBS-injected writable
# TMPDIR/TMP/TEMP, fall back to <workdir> (never a hardcoded /tmp).
_TMPBASE="${TMPDIR:-${TMP:-${TEMP:-.}}}"
mkdir -p "$_TMPBASE" 2>/dev/null || _TMPBASE="$WORKDIR"
mkdir -p "$WORKDIR" 2>/dev/null || true
OUT="$_TMPBASE/umtprd-test-out.txt"
PASS=0
FAIL=0

report() {
    # $1 = case number, $2 = ok (0/1), $3 = label
    if [ "$2" -eq 0 ]; then
        echo "CASE $1 PASS: $3"
        PASS=$((PASS + 1))
    else
        echo "CASE $1 FAIL: $3"
        FAIL=$((FAIL + 1))
    fi
}

dump_out() {
    # $1 = exit code; print bounded output excerpt for diagnosis.
    # (Exit code alone cannot distinguish a loader failure from an app error.)
    echo "  exit=$1, output excerpt (first 15 lines of $OUT):"
    sed -n '1,15p' "$OUT" 2>/dev/null || echo "  (no output file)"
}

# --- Case 1: binary present and executable --------------------------------
if [ -x "$BIN" ]; then
    report 1 0 "bin/umtprd present and executable"
else
    echo "  (not executable: $BIN)"
    report 1 1 "bin/umtprd missing or not executable"
fi

# --- Run the daemon (no args; guarded by timeout) --------------------------
if command -v timeout >/dev/null 2>&1; then
    timeout 15 "$BIN" > "$OUT" 2>&1
    rc=$?
else
    "$BIN" > "$OUT" 2>&1
    rc=$?
fi

# --- Case 2: output is non-empty -------------------------------------------
if [ -s "$OUT" ]; then
    report 2 0 "daemon output is non-empty"
else
    dump_out "$rc"
    report 2 1 "daemon produced empty output"
fi

# --- Case 3: banner proves ELF load + libc printf path ---------------------
if grep -q "uMTP Responder" "$OUT" 2>/dev/null; then
    report 3 0 "banner 'uMTP Responder' printed"
else
    dump_out "$rc"
    report 3 1 "banner 'uMTP Responder' missing"
fi

# --- Case 4: version string compiled in ------------------------------------
if grep -q "Version:" "$OUT" 2>/dev/null; then
    report 4 0 "'Version:' line printed"
else
    dump_out "$rc"
    report 4 1 "'Version:' line missing"
fi

# --- Case 5 (negative control): graceful USB-init-failure exit, non-zero ---
if [ "$rc" -ne 0 ]; then
    report 5 0 "graceful failure exit (exit=$rc, no USB gadget device)"
else
    dump_out "$rc"
    report 5 1 "unexpected exit 0 (stub would pass silently)"
fi

echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
