#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for pimd 2.3.2 (installed pimd program).
#   PIMD_BIN  path to the installed pimd executable
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -u

BIN="${PIMD_BIN:?PIMD_BIN must point to the installed pimd executable}"

WORK="${TMPDIR:-.}/pimd-test.$$"
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
check "installed pimd present" "$([ -x "$BIN" ] && echo yes || echo no)" "yes"

# 2. -v prints the version banner and exits 0
"$BIN" -v > "$WORK/v.out" 2>&1 && rc=0 || rc=$?
check "pimd -v exit status" "$rc" 0 "$WORK/v.out"
check "pimd -v banner" "$(grep -qF -- 'pimd version 2.3.2' "$WORK/v.out" && echo 0 || echo 1)" 0 "$WORK/v.out"

# 3. --help prints the usage block and exits 0
"$BIN" --help > "$WORK/h.out" 2>&1 && rc=0 || rc=$?
check "pimd --help exit status" "$rc" 0 "$WORK/h.out"
check "pimd --help usage text" "$(grep -qF -- 'Usage: pimd' "$WORK/h.out" && echo 0 || echo 1)" 0 "$WORK/h.out"

# 4. --version long form works too
"$BIN" --version > "$WORK/lv.out" 2>&1 || true
check "pimd --version banner" "$(grep -qF -- 'pimd version 2.3.2' "$WORK/lv.out" && echo 0 || echo 1)" 0 "$WORK/lv.out"

echo "PIMD_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
