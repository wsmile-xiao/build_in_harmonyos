#!/bin/sh
# test_xcolmix.sh — execute the packaged xcolmix binary on HarmonyOS (headless)
#
# Invoked by test_package/conanfile.py test() with:
#   $1 = absolute path to the packaged xcolmix binary
#   $2 = optional colon-joined LD_PRELOAD list of runtime .so paths
#   $3 = a path that is guaranteed not to exist (drives the access(2) branch)
#
# xcolmix is a GUI program: with an openable display and acceptable arguments it
# calls fl_do_forms() and blocks forever.  The three command lines below are all
# rejected by main() itself, before any form is shown, so they are deterministic
# on a headless worker and on a desktop that happens to have $DISPLAY set:
#
#   main()                              (src/xcolmix.c)
#     fl_initialize(...)                -> XForms, returns NULL if no display
#     if (argc > 2)          usage()    -> case 1 and case 3
#     else if (argc == 2 && access(argv[1], R_OK)) usage()  -> case 2
#
# usage() (src/usage.c) prints the banner built from src/version.h and exits 1.
#
# POSIX sh only, and deliberately *without* `set -e/-u/pipefail` (review rule 25
# asks for `set -euo pipefail`): every assertion here is a deliberate non-zero
# exit captured with `rc=$?`, which `set -e` would abort on before the check can
# run, and `pipefail` is not POSIX.  Same documented deviation as the merged
# archives/x/xev/1.2.7/test_package/test_xev.sh.  Every assertion also echoes
# the captured output, so a loader or relocation error lands in the log instead
# of being swallowed.
#
# Same shape as archives/x/xev/1.2.7/test_package/test_xev.sh.

XCOLMIX_BIN="$1"
LD_PRELOAD_EXTRA="${2:-}"
ABSENT_RGB="$3"

if [ -z "$XCOLMIX_BIN" ] || [ -z "$ABSENT_RGB" ]; then
    echo "FAIL: test_xcolmix.sh needs <binary> and <absent-rgb-path>"
    exit 1
fi

if [ ! -f "$XCOLMIX_BIN" ]; then
    echo "FAIL: $XCOLMIX_BIN not found"
    exit 1
fi

BIN_DIR=$(dirname "$XCOLMIX_BIN")
LD_LIBRARY_PATH="$BIN_DIR:${LD_LIBRARY_PATH:-}"
export LD_LIBRARY_PATH
if [ -n "$LD_PRELOAD_EXTRA" ]; then
    LD_PRELOAD="$LD_PRELOAD_EXTRA${LD_PRELOAD:+:$LD_PRELOAD}"
    export LD_PRELOAD
fi

echo "[shell] $0"
echo "[env] PATH=$PATH"
echo "[env] LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "[env] LD_PRELOAD=${LD_PRELOAD:-}"
echo "[env] DISPLAY=${DISPLAY:-<unset>}"

if command -v ldd >/dev/null 2>&1; then
    echo "[ldd]"
    ldd "$XCOLMIX_BIN" 2>&1 || true
fi

assertions=9
passed=0

fail() {
    echo "FAIL: $1"
}

# --- case 1/3: argc > 2 -> usage() -> exit(1) --------------------------
echo "[case 1/$((assertions / 3))] xcolmix alpha beta gamma (argc > 2 branch)"
out=$("$XCOLMIX_BIN" alpha beta gamma 2>&1 </dev/null)
rc=$?
echo "$out"
if [ "$rc" -eq 1 ]; then
    echo "PASS: exit status is 1 (usage() rejects argc > 2)"
    passed=$((passed + 1))
else
    fail "exit status is $rc, expected 1 for argc > 2"
fi
if echo "$out" | grep -q "X Color Mixer  V1.07"; then
    echo "PASS: banner reports V1.07 (src/version.h)"
    passed=$((passed + 1))
else
    fail "banner does not report 'X Color Mixer  V1.07'"
fi
if echo "$out" | grep -q "Usage: xcolmix"; then
    echo "PASS: usage banner printed"
    passed=$((passed + 1))
else
    fail "usage banner missing"
fi

# --- case 2/3: argc == 2 with an unreadable rgb database -> usage() ----
echo "[case 2/3] xcolmix $ABSENT_RGB (access(R_OK) rejection branch)"
out=$("$XCOLMIX_BIN" "$ABSENT_RGB" 2>&1 </dev/null)
rc=$?
echo "$out"
if [ "$rc" -eq 1 ]; then
    echo "PASS: exit status is 1 (unreadable rgb database rejected)"
    passed=$((passed + 1))
else
    fail "exit status is $rc, expected 1 for an unreadable rgb database"
fi
if echo "$out" | grep -q "Usage: xcolmix"; then
    echo "PASS: usage banner printed"
    passed=$((passed + 1))
else
    fail "usage banner missing"
fi
if echo "$out" | grep -q "or: xcolmix \[X options\] rgb-database-file"; then
    echo "PASS: both documented invocation forms are advertised"
    passed=$((passed + 1))
else
    fail "usage banner does not document the rgb-database-file form"
fi

# --- case 3/3: unreachable display -> fl_initialize() runs and reports --
# The display is forced to a closed loopback port so the assertion does not
# depend on whether the worker has $DISPLAY set.
echo "[case 3/3] xcolmix -display 127.0.0.1:99 alpha beta gamma (XForms runtime)"
out=$("$XCOLMIX_BIN" -display 127.0.0.1:99 alpha beta gamma 2>&1 </dev/null)
rc=$?
echo "$out"
if [ "$rc" -eq 1 ]; then
    echo "PASS: exit status is 1"
    passed=$((passed + 1))
else
    fail "exit status is $rc, expected 1"
fi
if echo "$out" | grep -q "Can't open display 127.0.0.1:99"; then
    echo "PASS: XForms fl_initialize() ran inside the process and reported the unreachable display"
    passed=$((passed + 1))
else
    fail "no fl_initialize() diagnostic for the forced unreachable display"
fi
if echo "$out" | grep -q "X Color Mixer  V1.07"; then
    echo "PASS: banner reports V1.07"
    passed=$((passed + 1))
else
    fail "banner does not report 'X Color Mixer  V1.07'"
fi

echo ""
echo "xcolmix runtime assertions: $passed/$assertions"
if [ "$passed" -ne "$assertions" ]; then
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_xcolmix.sh","discovered":%d,"passedCount":%d}\n' \
        "$assertions" "$passed"
    exit 1
fi
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xcolmix.sh","discovered":%d,"passedCount":%d}\n' \
    "$assertions" "$passed"
echo "OK: all $assertions checks passed"
exit 0
