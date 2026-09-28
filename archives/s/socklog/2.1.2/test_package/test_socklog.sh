#!/bin/sh
# Consumer smoke test for socklog/2.1.2.
#
# Usage: sh test_socklog.sh <absolute-package-bin-dir>
#
# Scope is deliberately bounded: socklog is a syslog collection daemon, so its
# receiving face needs an UNIX datagram socket (/dev/log), a UDP bind, or the
# ucspi protocol, and the shipped service scripts drop privileges via setuid.
# This test therefore proves only that the packaged programs exist, are
# executable, and answer on their version/usage face. It does NOT claim
# end-to-end log collection works; see notes.md for the runtime scope statement.
set -u

BIN_DIR="$1"
COMMANDS="socklog socklog-check socklog-conf tryto uncat"
pass=0
fail=0

ok() {
    pass=$((pass + 1))
    echo "ok   - $1"
}

bad() {
    fail=$((fail + 1))
    echo "FAIL - $1"
}

if [ ! -d "$BIN_DIR" ]; then
    echo "FAIL - package bin dir does not exist: $BIN_DIR"
    exit 1
fi

for cmd in $COMMANDS; do
    prog="$BIN_DIR/$cmd"
    if [ -f "$prog" ] && [ -x "$prog" ]; then
        ok "$cmd packaged and executable ($prog)"
    else
        bad "$cmd missing or not executable: $prog"
        continue
    fi

    # -V prints the embedded version token and then the usage, exiting 1.
    # The usage line echoes argv[0], so match only the leading "usage:" label
    # rather than a fixed program spelling.
    out=$("$prog" -V </dev/null 2>&1)
    rc=$?
    if [ "$rc" -eq 1 ] \
        && printf '%s\n' "$out" | grep -q '\$Id:' \
        && printf '%s\n' "$out" | grep -q '^usage: '; then
        ok "$cmd -V reports version token and usage (rc=1)"
    else
        bad "$cmd -V unexpected (rc=$rc): $(printf '%s' "$out" | head -n 1)"
    fi
done

echo "socklog test_package: passed=$pass failed=$fail total=$((pass + fail))"
[ "$fail" -eq 0 ] || exit 1
exit 0
