#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for SweeD 3.2.1 (installed SweeD program).
#   SWEED_BIN  path to the installed SweeD executable
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -u

BIN="${SWEED_BIN:?SWEED_BIN must point to the installed SweeD executable}"

WORK="${TMPDIR:-.}/sweed-test.$$"
mkdir -p "$WORK" || { echo "FAIL: cannot create workdir $WORK"; exit 1; }
cd "$WORK" || exit 1
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
check "installed SweeD present" "$([ -x "$BIN" ] && echo yes || echo no)" "yes"

# 2/3/4. -h / help prints the full option list
"$BIN" -h > "$WORK/h.out" 2>&1 || true
check "SweeD help lists -name"  "$(grep -qF -- '-name runName'   "$WORK/h.out" && echo 0 || echo 1)" 0 "$WORK/h.out"
check "SweeD help lists -input" "$(grep -qF -- '-input inputFile' "$WORK/h.out" && echo 0 || echo 1)" 0 "$WORK/h.out"
check "SweeD help lists -grid"  "$(grep -qF -- '-grid gridNumber' "$WORK/h.out" && echo 0 || echo 1)" 0 "$WORK/h.out"

# 5. a missing -name is reported
"$BIN" > "$WORK/n.out" 2>&1 || true
check "SweeD missing-name diagnostic" "$(grep -qF -- 'specify a name' "$WORK/n.out" && echo 0 || echo 1)" 0 "$WORK/n.out"

echo "SWEED_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
