#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for vrfy 990522 (installed vrfy CLI).
#
# Env: VRFY_BIN = path to the installed vrfy executable
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -euo pipefail

BIN="${VRFY_BIN:?VRFY_BIN must point to the installed vrfy executable}"

WORK="${TMPDIR:-.}/vrfy-test.$$"
mkdir -p "$WORK" || { echo "FAIL: cannot create workdir $WORK"; exit 1; }
trap 'rm -rf "$WORK"' EXIT

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

# 1. -V prints the version string
"$BIN" -V > "$WORK/ver.txt" 2>&1 || true
check "vrfy -V prints Version" "$(contains "$WORK/ver.txt" 'Version')" 0 "$WORK/ver.txt"

# 2. running with no address prints the usage text
"$BIN" > "$WORK/usage.txt" 2>&1 || true
check "vrfy (no args) prints Usage" "$(contains "$WORK/usage.txt" 'Usage')" 0 "$WORK/usage.txt"

echo "VRFY_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
