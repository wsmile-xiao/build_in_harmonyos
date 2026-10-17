#!/bin/sh
# test_tina.sh — smoke test for the packaged tina binary.
#
# tina is a full-screen curses TUI, so initscr() cannot run headless.
# main() in main.c handles --help / --version BEFORE initscr() and
# returns 0 — this exercises the packaged binary end-to-end (ELF load,
# dynamic linker, ncurses linkage) without a terminal (sl/npush同款).
#
# Usage: test_tina.sh <path-to-tina-binary>
set -u

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <tina-binary>" >&2
    exit 2
fi

TINA="$1"

if [ ! -x "$TINA" ]; then
    echo "FAIL: tina binary not found or not executable: $TINA" >&2
    exit 1
fi

OUT="$("$TINA" --version 2>&1)"
RC=$?

if [ "$RC" -ne 0 ]; then
    echo "FAIL: tina --version exited with $RC:" >&2
    echo "$OUT" >&2
    exit 1
fi

case "$OUT" in
    *"Tina 0.1.14"*)
        echo "OK: tina --version output verified"
        echo "$OUT"
        ;;
    *)
        echo "FAIL: tina --version output unexpected:" >&2
        echo "$OUT" >&2
        exit 1
        ;;
esac

exit 0
