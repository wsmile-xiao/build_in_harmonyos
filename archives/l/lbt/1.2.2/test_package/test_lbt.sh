#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for lbt 1.2.2 (installed lbt / lbt2dot filters).
#
# Env:
#   LBT_BIN      path to the installed lbt executable
#   LBT2DOT_BIN  path to the installed lbt2dot executable
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

LBT="${LBT_BIN:?LBT_BIN must point to the installed lbt executable}"
LBT2DOT="${LBT2DOT_BIN:?LBT2DOT_BIN must point to the installed lbt2dot executable}"

WORK="${TMPDIR:-.}/lbt-test.$$"
mkdir -p "$WORK" || { echo "FAIL: cannot create workdir $WORK"; exit 1; }
cd "$WORK"
trap 'cd /; rm -rf "$WORK"' EXIT

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

# 1-2. lbt with an argument prints usage and fails
"$LBT" extra > u.out 2> u.err && rc=0 || rc=$?
check "lbt with an argument exits 1" "$rc" 1
check "lbt prints usage" "$(grep -c -F 'usage:' u.err)" 1

# 3-5. translate G p0
printf 'G p0' | "$LBT" > auto.txt 2> auto.err && rc=0 || rc=$?
check "lbt translates 'G p0'" "$rc" 0 auto.err
check "lbt output header is two integers" "$(head -1 auto.txt | grep -c -E '^[0-9]+ [0-9]+$')" 1
check "lbt output contains the -1 terminator" "$(grep -q -F -- '-1' auto.txt && echo 0 || echo 1)" 0

# 6-9. convert the automaton to GraphViz
"$LBT2DOT" < auto.txt > auto.dot 2> d.err && rc=0 || rc=$?
check "lbt2dot exits 0" "$rc" 0 d.err
check "lbt2dot emits a digraph header" "$(head -1 auto.dot)" "digraph g {"
check "lbt2dot marks the initial state" "$(grep -c -F 'style=filled,' auto.dot)" 1
check "lbt2dot closes the digraph" "$(tail -1 auto.dot)" "}"

# 10-11. invalid formula
printf 'Q' | "$LBT" > q.out 2> q.err && rc=0 || rc=$?
check "lbt rejects an invalid formula (exit 2)" "$rc" 2
check "lbt reports the unknown character" "$(grep -c -F 'unknown character' q.err)" 1

# 12-13. invalid automaton input for lbt2dot
printf 'x' | "$LBT2DOT" > b.out 2> b.err && rc=0 || rc=$?
check "lbt2dot rejects invalid input" "$rc" 1
check "lbt2dot reports the parse error" "$(grep -c -F 'error in automaton' b.err)" 1

echo "LBT_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
