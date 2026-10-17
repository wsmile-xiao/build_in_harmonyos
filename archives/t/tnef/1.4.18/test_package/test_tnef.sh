#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for tnef 1.4.18 (installed tnef CLI).
#
# Env: TNEF_BIN = path to the installed tnef executable
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -euo pipefail

BIN="${TNEF_BIN:?TNEF_BIN must point to the installed tnef executable}"

checks=0
fails=0

check() { # check <name> <actual> <expected>
	checks=$((checks + 1))
	if [ "$2" = "$3" ]; then
		echo "PASS: $1"
	else
		echo "FAIL: $1 (got '$2', want '$3')"
		fails=$((fails + 1))
	fi
}

contains() { # contains <file> <pattern>
	if grep -q -F -- "$2" "$1"; then echo 0; else echo 1; fi
}

WORK="${TMPDIR:-.}/tnef-test.$$"
mkdir -p "$WORK" || { echo "FAIL: cannot create workdir $WORK"; exit 1; }
trap 'rm -rf "$WORK"' EXIT

# 1. --version reports 1.4.18
"$BIN" --version > "$WORK/ver.txt" 2>&1 || true
check "tnef --version reports 1.4.18" "$(contains "$WORK/ver.txt" '1.4.18')" 0

# 2. --help prints usage
"$BIN" --help > "$WORK/help.txt" 2>&1 || true
check "tnef --help prints usage" "$(contains "$WORK/help.txt" '[options] [FILE]')" 0

# 3. a missing input file fails gracefully (non-zero, no crash)
if "$BIN" -f "$WORK/does-not-exist.tnef" > "$WORK/missing.txt" 2>&1; then r=0; else r=1; fi
check "tnef fails gracefully on missing input" "$r" 1

echo "TNEF_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
