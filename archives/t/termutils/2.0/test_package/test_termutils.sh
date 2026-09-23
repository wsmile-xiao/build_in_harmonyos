#!/bin/sh
# Consumer test for GNU termutils 2.0 — asserts real tool behaviour.
#
# tput reads the terminal entry named by $TERM from $TERMCAP (termcap
# database semantics of the bundled termcap.c). A minimal in-memory entry
# makes every assertion deterministic without any system terminal database.
set -e
BIN="$1"
if [ -z "$BIN" ] || [ ! -x "$BIN/tput" ]; then
    echo "usage: test_termutils.sh <package-bindir>" >&2
    exit 2
fi

export TERM=gtu
export TERMCAP='gtu:co#80:li#24:'

# 1. numeric capability "co" (columns) must be reported verbatim
out=$("$BIN/tput" co)
[ "$out" = "80" ] || { echo "FAIL: tput co expected 80, got '$out'" >&2; exit 1; }

# 2. numeric capability "li" (lines) must be reported verbatim
out=$("$BIN/tput" li)
[ "$out" = "24" ] || { echo "FAIL: tput li expected 24, got '$out'" >&2; exit 1; }

# 3. an unknown capability must not be silently accepted (exit code 4)
if "$BIN/tput" no_such_cap_zz >/dev/null 2>&1; then
    echo "FAIL: tput accepted an unknown capability" >&2
    exit 1
fi

echo "termutils 2.0 consumer test: OK (tput co/li/unknown-capability assertions)"
