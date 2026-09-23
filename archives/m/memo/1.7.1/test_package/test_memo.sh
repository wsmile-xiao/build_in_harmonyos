#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for memo 1.7.1 (installed memo CLI).
#
# Env: MEMO_BIN = path to the installed memo executable
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -euo pipefail

BIN="${MEMO_BIN:?MEMO_BIN must point to the installed memo executable}"

WORK="${TMPDIR:-.}/memo-test.$$"
mkdir -p "$WORK" || { echo "FAIL: cannot create workdir $WORK"; exit 1; }
trap 'rm -rf "$WORK"' EXIT
# memo keeps its notes in $HOME/.memo
HOME="$WORK"
export HOME

checks=0
fails=0

check() { # check <name> <actual> <expected> [dumpfile]
	checks=$((checks + 1))
	if [ "$2" = "$3" ]; then
		echo "PASS: $1"
	else
		echo "FAIL: $1 (got '$2', want '$3')"
		if [ -n "${4:-}" ] && [ -f "$4" ]; then
			echo "--- $4 ---"; head -20 "$4"; echo "--- end ---"
		fi
		fails=$((fails + 1))
	fi
}

contains() { # contains <file> <pattern>
	if grep -q -F -- "$2" "$1"; then echo 0; else echo 1; fi
}

# 1. --version reports 1.7.1
"$BIN" --version > "$WORK/ver.txt" 2>&1 || true
check "memo --version reports 1.7.1" "$(contains "$WORK/ver.txt" '1.7.1')" 0 "$WORK/ver.txt"

# 2. --help prints the synopsis
"$BIN" --help > "$WORK/help.txt" 2>&1 || true
check "memo --help prints SYNOPSIS" "$(contains "$WORK/help.txt" 'SYNOPSIS')" 0 "$WORK/help.txt"

# 3. add a note and list it back
"$BIN" -a "hello memo" > "$WORK/add.txt" 2>&1 || true
"$BIN" -s > "$WORK/list.txt" 2>&1 || true
check "memo -a/-s round-trips a note" "$(contains "$WORK/list.txt" 'hello memo')" 0 "$WORK/list.txt"

echo "MEMO_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
