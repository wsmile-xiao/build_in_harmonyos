#!/bin/sh
# Verify the packaged Zangband binary launches and reports its ncurses(GNU Curses) port.
set -eu

if [ "$#" -lt 1 ]; then
    echo "usage: test.sh <path-to-zangband>" >&2
    exit 2
fi

OUT="$("$1" -h 2>&1)"

printf '%s\n' "$OUT" | grep -q "Usage: angband"
printf '%s\n' "$OUT" | grep -q -- "-mgcu"

echo "zangband usage OK (ncurses/GCU port present)"
