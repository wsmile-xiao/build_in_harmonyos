#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for mhz 1.0.0 (installed mhz program).
#   MHZ_BIN  path to the installed mhz executable
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -u

BIN="${MHZ_BIN:?MHZ_BIN must point to the installed mhz executable}"

WORK="${TMPDIR:-.}/mhz-test.$$"
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

# 1. the installed program is present and executable
check "installed mhz present" "$([ -x "$BIN" ] && echo yes || echo no)" "yes"

# 2. -h prints the usage banner and exits 0
"$BIN" -h > "$WORK/h.out" 2>&1 && rc=0 || rc=$?
check "mhz -h exit status" "$rc" 0 "$WORK/h.out"
check "mhz -h usage text" "$(grep -qF -- 'Usage:' "$WORK/h.out" && echo 0 || echo 1)" 0 "$WORK/h.out"

# 3. a short measurement prints a numeric CPU frequency and exits 0
"$BIN" -c 1 0 1000 > "$WORK/c.out" 2>&1 && rc=0 || rc=$?
check "mhz -c measurement exit status" "$rc" 0 "$WORK/c.out"
check "mhz -c prints numeric MHz" "$(grep -qE '^[0-9]+(\.[0-9]+)?$' "$WORK/c.out" && echo 0 || echo 1)" 0 "$WORK/c.out"

echo "MHZ_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
