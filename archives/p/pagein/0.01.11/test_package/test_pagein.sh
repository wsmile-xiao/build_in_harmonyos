#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for pagein 0.01.11 (installed pagein program).
#   PAGEIN_BIN  path to the installed pagein executable
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -u

BIN="${PAGEIN_BIN:?PAGEIN_BIN must point to the installed pagein executable}"

WORK="${TMPDIR:-.}/pagein-test.$$"
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
check "installed pagein present" "$([ -x "$BIN" ] && echo yes || echo no)" "yes"

# 2. -h prints the usage banner and exits 0
"$BIN" -h > "$WORK/h.out" 2>&1 && rc=0 || rc=$?
check "pagein -h exit status" "$rc" 0 "$WORK/h.out"
check "pagein -h usage text" "$(grep -qF -- 'Usage: pagein' "$WORK/h.out" && echo 0 || echo 1)" 0 "$WORK/h.out"

# 3. no -a/-p option is rejected
"$BIN" > "$WORK/n.out" 2> "$WORK/n.err" && rc=0 || rc=$?
check "pagein no-target exit status" "$rc" 1
check "pagein no-target diagnostic" "$(grep -qF -- 'must use one of -a or -p' "$WORK/n.err" && echo 0 || echo 1)" 0 "$WORK/n.err"

# 4. -a and -p together are rejected
"$BIN" -a -p 1 > "$WORK/b.out" 2> "$WORK/b.err" && rc=0 || rc=$?
check "pagein -a -p conflict" "$(grep -qF -- 'must not use -a and -p options together' "$WORK/b.err" && echo 0 || echo 1)" 0 "$WORK/b.err"

# 5. an invalid pid is rejected
"$BIN" -p 0 > "$WORK/p.out" 2> "$WORK/p.err" && rc=0 || rc=$?
check "pagein bad pid diagnostic" "$(grep -qF -- 'bad pid' "$WORK/p.err" && echo 0 || echo 1)" 0 "$WORK/p.err"

echo "PAGEIN_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
