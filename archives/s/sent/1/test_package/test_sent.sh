#!/bin/sh
# test_sent.sh — sent 1 packaged-binary acceptance test (POSIX sh).
#
# Contract with test_package/conanfile.py:
#   $1 = absolute path to the packaged `sent` binary
#   $2 = optional colon-joined absolute .so list used as LD_PRELOAD
#
# Device constraints this script obeys (all learned from the xeyes/xidle
# audit trail, do not "modernise" them away):
#   * POSIX sh only — it is executed with the SHELL that HMBS injects
#     (/bin/sh).  Never hardcode /data/service/hnp/bin/bash.
#   * No `set -e`, no `set -u`, no `set -o pipefail`: toybox ash rejects
#     them and the whole script dies before any assertion runs.
#   * Every assertion captures its own exit status and ALWAYS echoes the
#     captured output, so a dynamic-loader complaint lands in the CI log
#     instead of being swallowed.
#   * Runtime library lookup is double-buffered: LD_LIBRARY_PATH from the
#     conanrun environment plus LD_PRELOAD absolute paths, because the
#     device loader may ignore LD_LIBRARY_PATH (HMBS [stale_runtime_library]).
#
# sent is a GUI viewer, so it cannot be exercised the way a CLI tool can.
# What is asserted here are the four code paths that upstream reaches
# *before* xinit()/XOpenDisplay() (sent.c main()):
#   -v                 -> prints "sent-1" to stderr and returns 0
#   unknown option     -> usage() -> die() -> exit 1
#   "-" with empty stdin -> load() yields slidecount 0 -> usage() -> exit 1
#   missing file       -> fopen fails -> die() -> exit 1
# A presentation that actually parses is deliberately NOT fed in: main()
# would then call xinit(), and on a host that happens to export DISPLAY the
# binary would open a window and block forever, hanging CI.  Successful
# dynamic linking is already proven by the -v run, because a missing
# DT_NEEDED would abort the process before main() is entered.

SENT_BIN="$1"
LD_PRELOAD_EXTRA="${2:-}"
DYNLOAD_DIR="${3:-}"

if [ -z "$SENT_BIN" ]; then
    echo "FAIL: sent binary path not provided"
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":false,"passed":false,"command":"test_sent.sh","discovered":0,"passedCount":0}'
    exit 1
fi

if [ ! -x "$SENT_BIN" ]; then
    echo "FAIL: $SENT_BIN not found or not executable"
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":false,"passed":false,"command":"test_sent.sh","discovered":0,"passedCount":0}'
    exit 1
fi

BIN_DIR=$(dirname "$SENT_BIN")
PKG_DIR=$(dirname "$BIN_DIR")
export LD_LIBRARY_PATH="${BIN_DIR}:${PKG_DIR}/lib:${LD_LIBRARY_PATH:-}"
if [ -n "$DYNLOAD_DIR" ]; then
    # Re-signed SONAME-named copies of the runtime closure go first: the
    # published fontconfig/libxft binaries carry signatures the device
    # loader rejects (E135 family), so their fresh copies win resolution.
    export LD_LIBRARY_PATH="${DYNLOAD_DIR}:${LD_LIBRARY_PATH}"
fi
if [ -n "$LD_PRELOAD_EXTRA" ]; then
    export LD_PRELOAD="$LD_PRELOAD_EXTRA"
fi

discovered=6
passed=0

echo "[shell] $0"
echo "[bin] $SENT_BIN"
echo "[env] LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "[env] LD_PRELOAD=${LD_PRELOAD:-<empty>}"
echo "[env] DISPLAY=${DISPLAY-<unset>}"

# ldd output is diagnostic only, never an assertion.
if command -v ldd >/dev/null 2>&1; then
    echo "[ldd]"
    ldd "$SENT_BIN" 2>&1 || true
fi

# --- 1: -v really runs and reports the baked-in version ------------------
echo "[test 1/$discovered] [exec] sent -v"
out=$("$SENT_BIN" -v 2>&1)
rc=$?
echo "$out"
if [ $rc -eq 0 ] && echo "$out" | grep -q '^sent-1$'; then
    echo "PASS: sent -v exit=0 and printed sent-1"
    passed=$((passed + 1))
else
    echo "FAIL: sent -v exit=$rc output=[$out] (expected 0 / 'sent-1'; an empty version suffix means -DVERSION was dropped from CFLAGS)"
fi

# --- 2: unknown option -> usage(); usage line must carry the real argv0 --
# grep for $SENT_BIN itself: only the genuinely executed binary can echo its
# own argv[0], so this rejects a stubbed or relocated artefact.
echo "[test 2/$discovered] [exec] sent -Z (unknown option)"
out=$("$SENT_BIN" -Z 2>&1)
rc=$?
echo "$out"
if [ $rc -eq 1 ] && echo "$out" | grep -q "usage: $SENT_BIN \[file\]"; then
    echo "PASS: unknown option exits 1 with usage naming the tested binary"
    passed=$((passed + 1))
else
    echo "FAIL: sent -Z exit=$rc output=[$out] (expected 1 / 'usage: $SENT_BIN [file]')"
fi

# --- 3: unreadable presentation file -> die() before any X call ----------
echo "[test 3/$discovered] [exec] sent <definitely-missing-file>"
out=$("$SENT_BIN" /nonexistent/sent-acceptance-case-404.txt 2>&1)
rc=$?
echo "$out"
if [ $rc -eq 1 ] && echo "$out" | grep -q "Unable to open"; then
    echo "PASS: missing file exits 1 with 'Unable to open'"
    passed=$((passed + 1))
else
    echo "FAIL: missing-file exit=$rc output=[$out] (expected 1 / 'Unable to open')"
fi

# --- 4: empty stdin as presentation source -> slidecount 0 -> usage() ----
echo "[test 4/$discovered] [exec] sent - < /dev/null"
out=$("$SENT_BIN" - < /dev/null 2>&1)
rc=$?
echo "$out"
if [ $rc -eq 1 ] && echo "$out" | grep -q "usage: $SENT_BIN \[file\]"; then
    echo "PASS: empty presentation exits 1 via usage() without touching X"
    passed=$((passed + 1))
else
    echo "FAIL: empty-stdin exit=$rc output=[$out] (expected 1 / usage line)"
fi

# --- 5/6: installed artefacts (existence only, NOT binary execution) -----
echo "[test 5/$discovered] [file] share/man/man1/sent.1"
if [ -s "$PKG_DIR/share/man/man1/sent.1" ]; then
    echo "PASS: man page installed"
    passed=$((passed + 1))
else
    echo "FAIL: $PKG_DIR/share/man/man1/sent.1 missing (MANPREFIX wiring broken)"
fi

echo "[test 6/$discovered] [file] licenses/LICENSE"
if [ -s "$PKG_DIR/licenses/LICENSE" ]; then
    echo "PASS: license file packaged"
    passed=$((passed + 1))
else
    echo "FAIL: $PKG_DIR/licenses/LICENSE missing"
fi

if [ "$passed" -ne "$discovered" ]; then
    echo "FAIL: $((discovered - passed))/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_sent.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_sent.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
