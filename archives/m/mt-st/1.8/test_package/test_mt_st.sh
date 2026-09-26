#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for mt-st 1.8 (installed mt / stinit programs).
#
# Env:
#   MT_BIN           path to the installed mt executable
#   STINIT_BIN       path to the installed stinit executable
#   STINIT_EXAMPLES  path to the installed stinit.def.examples
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

MT="${MT_BIN:?MT_BIN must point to the installed mt executable}"
STINIT="${STINIT_BIN:?STINIT_BIN must point to the installed stinit executable}"
DEF="${STINIT_EXAMPLES:?STINIT_EXAMPLES must point to stinit.def.examples}"

WORK="${TMPDIR:-.}/mt-st-test.$$"
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

# 1. mt --version prints the tool banner
"$MT" --version > "$WORK/ver.txt" 2>&1 || true
check "mt --version prints mt-st banner" "$(contains "$WORK/ver.txt" 'mt-st v.')" 0 "$WORK/ver.txt"

# 2. mt -h exits 0 and lists the command table
"$MT" -h > "$WORK/help.out" 2> "$WORK/help.err" && rc=0 || rc=$?
check "mt -h exit status" "$rc" 0
check "mt -h lists commands" "$(contains "$WORK/help.err" 'commands:')" 0 "$WORK/help.err"

# 3. mt densities does not need a tape device
"$MT" densities > "$WORK/dens.txt" 2>&1 || true
check "mt densities lists LTO media" "$(contains "$WORK/dens.txt" 'LTO')" 0 "$WORK/dens.txt"

# 4. stinit --version prints the tool banner
"$STINIT" --version > "$WORK/sver.txt" 2>&1 || true
check "stinit --version prints banner" "$(contains "$WORK/sver.txt" 'stinit v.')" 0 "$WORK/sver.txt"

# 5. stinit parses the shipped example database cleanly
"$STINIT" -v -v -p -f "$DEF" > "$WORK/parse.txt" 2> "$WORK/parse.err" || true
check "stinit parses stinit.def.examples" "$(contains "$WORK/parse.txt" 'No errors found.')" 0 "$WORK/parse.txt"

# 6. unknown mt command is rejected
"$MT" to-the-moon > "$WORK/bad.out" 2> "$WORK/bad.err" && rc=0 || rc=$?
check "mt rejects unknown command" "$rc" 1

# 7. missing stinit database is reported
"$STINIT" -p -f no-such-database > "$WORK/db.out" 2> "$WORK/db.err" && rc=0 || rc=$?
check "stinit reports missing database" "$rc" 1

echo "MT_ST_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
