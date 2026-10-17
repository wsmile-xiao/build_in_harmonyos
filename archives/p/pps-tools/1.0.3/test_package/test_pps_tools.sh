#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for pps-tools 1.0.3 (installed programs + PPSAPI header).
#
# Env:
#   PPS_BINDIR      directory containing the installed pps-tools programs
#   HEADER_TEST_BIN compiled consumer for include/sys/timepps.h
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -u

BINDIR="${PPS_BINDIR:?PPS_BINDIR must point to the installed bin directory}"
HEADER_TEST_BIN="${HEADER_TEST_BIN:?HEADER_TEST_BIN must point to the header consumer}"

WORK="${TMPDIR:-.}/pps-tools-test.$$"
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

PPSTEST="$BINDIR/ppstest"
PPSCTL="$BINDIR/ppsctl"
PPSWATCH="$BINDIR/ppswatch"
PPSLDISC="$BINDIR/ppsldisc"
PPSFIND="$BINDIR/ppsfind"

# 1. the four compiled programs (plus ppsfind) are installed and executable
missing=""
for prog in "$PPSTEST" "$PPSCTL" "$PPSWATCH" "$PPSLDISC" "$PPSFIND"; do
	[ -x "$prog" ] || missing="$missing $(basename "$prog")"
done
check "installed programs present" "${missing:-none}" "none"

# 2. ppstest without arguments prints usage and fails
"$PPSTEST" > "$WORK/t1.out" 2> "$WORK/t1.err" && rc=0 || rc=$?
check "ppstest usage exit status" "$rc" 1
check "ppstest usage text" "$(contains "$WORK/t1.err" 'usage:')" 0 "$WORK/t1.err"

# 3. ppsctl -h prints the command table and exits 0
"$PPSCTL" -h > "$WORK/t3.out" 2> "$WORK/t3.err" && rc=0 || rc=$?
check "ppsctl -h exit status" "$rc" 0
check "ppsctl -h lists commands" "$(contains "$WORK/t3.err" 'Commands:')" 0 "$WORK/t3.err"

# 4. ppswatch -h prints usage and exits 0
"$PPSWATCH" -h > "$WORK/t4.out" 2> "$WORK/t4.err" && rc=0 || rc=$?
check "ppswatch -h exit status" "$rc" 0

# 5. ppsldisc without arguments prints usage and fails
"$PPSLDISC" > "$WORK/t5.out" 2> "$WORK/t5.err" && rc=0 || rc=$?
check "ppsldisc usage exit status" "$rc" 1

# 6. ppsfind without arguments prints usage and fails
"$PPSFIND" > "$WORK/t6.out" 2> "$WORK/t6.err" && rc=0 || rc=$?
check "ppsfind usage exit status" "$rc" 1

# 7. ppsctl without a command reports the missing command (upstream prints the
#    diagnostic on stdout and the usage on stderr)
"$PPSCTL" > "$WORK/t7.out" 2> "$WORK/t7.err" && rc=0 || rc=$?
check "ppsctl no-command diagnostic" "$(contains "$WORK/t7.out" 'No command specified!')" 0 "$WORK/t7.out"

# 8. ppswatch without a device reports the missing device (stdout diagnostic)
"$PPSWATCH" > "$WORK/t8.out" 2> "$WORK/t8.err" && rc=0 || rc=$?
check "ppswatch no-device diagnostic" "$(contains "$WORK/t8.out" 'Device name missing!')" 0 "$WORK/t8.out"

# 9. the PPSAPI header is installed at sys/timepps.h
check "installed sys/timepps.h present" "$([ -f "$BINDIR/../include/sys/timepps.h" ] && echo yes || echo no)" "yes"

# 10. the compiled header consumer runs successfully
"$HEADER_TEST_BIN" > "$WORK/t10.out" 2>&1 && rc=0 || rc=$?
check "PPSAPI header consumer" "$rc" 0 "$WORK/t10.out"

echo "PPS_TOOLS_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
