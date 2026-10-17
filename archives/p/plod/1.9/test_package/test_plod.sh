#!/system/bin/sh
set -u

if [ "$#" -ne 2 ]; then
    echo "usage: $0 <perl> <plod>" >&2
    exit 2
fi

PERL=$1
PLOD=$2
TEST_ROOT="$PWD/plod-test-$$"
SYNTAX_OUT="$TEST_ROOT/syntax.out"
mkdir -p "$TEST_ROOT/home" "$TEST_ROOT/logs" || exit 1
trap 'rm -rf "$TEST_ROOT"' EXIT HUP INT TERM

TOTAL=5
PASSED=0
FAILED=0

pass_test() {
    PASSED=$((PASSED + 1))
    echo "PASS: $1"
}

fail_test() {
    FAILED=$((FAILED + 1))
    echo "FAIL: $1" >&2
}

echo "TEST 1: packaged-script-executable"
if [ -x "$PLOD" ] && IFS= read -r FIRST_LINE < "$PLOD" && \
   [ "$FIRST_LINE" = "#!/data/service/hnp/bin/perl" ]; then
    pass_test packaged-script-executable
else
    fail_test packaged-script-executable
fi

echo "TEST 2: perl-syntax-check"
if "$PERL" -c "$PLOD" >"$SYNTAX_OUT" 2>&1 && \
   grep -F "syntax OK" "$SYNTAX_OUT" >/dev/null; then
    pass_test perl-syntax-check
else
    cat "$SYNTAX_OUT" >&2
    fail_test perl-syntax-check
fi

HOME="$TEST_ROOT/home"
LOGDIR="$TEST_ROOT/logs"
LOGFILE="plod.log"
PLODRC="$TEST_ROOT/no-plodrc"
DEADLOG="$TEST_ROOT/dead.log"
TMPFILE="$TEST_ROOT/plod.tmp"
unset CRYPTCMD
BACKUP=""
STAMP=""
export HOME LOGDIR LOGFILE PLODRC DEADLOG TMPFILE BACKUP STAMP

ENTRY="HarmonyOS plod functional test"
echo "TEST 3: one-line-entry-write"
if "$PERL" "$PLOD" "$ENTRY" && \
   grep -F "$ENTRY" "$LOGDIR/$LOGFILE" >/dev/null; then
    pass_test one-line-entry-write
else
    fail_test one-line-entry-write
fi

echo "TEST 4: cat-round-trip"
if CAT_OUT=$("$PERL" "$PLOD" -C) && \
   printf '%s\n' "$CAT_OUT" | grep -F "$ENTRY" >/dev/null; then
    pass_test cat-round-trip
else
    fail_test cat-round-trip
fi

echo "TEST 5: ohos-adaptation-markers"
HOST_PERL_LEFT=no
grep -F '/usr/local/bin/perl' "$PLOD" >/dev/null 2>&1 && HOST_PERL_LEFT=yes
HOST_CRYPT_LEFT=no
grep -F '/usr/bin/crypt' "$PLOD" >/dev/null 2>&1 && HOST_CRYPT_LEFT=yes
CRYPT_DEFAULT_EMPTY=no
grep -F 'CRYPTCMD = "";' "$PLOD" >/dev/null 2>&1 && CRYPT_DEFAULT_EMPTY=yes
if [ "$HOST_PERL_LEFT" = no ] && [ "$HOST_CRYPT_LEFT" = no ] && [ "$CRYPT_DEFAULT_EMPTY" = yes ]; then
    pass_test ohos-adaptation-markers
else
    echo "  host-perl-left=$HOST_PERL_LEFT host-crypt-left=$HOST_CRYPT_LEFT crypt-default-empty=$CRYPT_DEFAULT_EMPTY" >&2
    fail_test ohos-adaptation-markers
fi

if [ "$FAILED" -eq 0 ]; then
    PASSED_BOOL=true
else
    PASSED_BOOL=false
fi

echo "PLOD_TEST_RESULT total=$TOTAL passed=$PASSED failed=$FAILED skipped=0"
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$PASSED_BOOL,\"command\":\"sh test_plod.sh <perl> <plod>\",\"discovered\":$TOTAL,\"passedCount\":$PASSED}"
echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"PLOD 1.9 release audited: 8 files; no test/tests directory, no test source files, and Makefile exposes only all, plod, install and clean targets."}'

if [ "$FAILED" -ne 0 ]; then
    exit 1
fi
