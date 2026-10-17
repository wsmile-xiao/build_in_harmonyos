#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for PBSIM 1.0.3-git20180330.e014b1d (installed pbsim).
#   PBSIM_BIN  path to the installed pbsim executable
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -u

BIN="${PBSIM_BIN:?PBSIM_BIN must point to the installed pbsim executable}"

WORK="${TMPDIR:-.}/pbsim-test.$$"
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
check "installed pbsim present" "$([ -x "$BIN" ] && echo yes || echo no)" "yes"

# 2. --version prints the version banner and exits 0
"$BIN" --version > "$WORK/v.out" 2>&1 && rc=0 || rc=$?
check "pbsim --version exit status" "$rc" 0 "$WORK/v.out"
check "pbsim --version banner" "$(grep -qF -- 'pbsim 1.0' "$WORK/v.out" && echo 0 || echo 1)" 0 "$WORK/v.out"

# 3. --help prints the usage block
"$BIN" --help > "$WORK/h.out" 2>&1 || true
check "pbsim --help usage text" "$(grep -qF -- 'USAGE: pbsim' "$WORK/h.out" && echo 0 || echo 1)" 0 "$WORK/h.out"

# 4. no reference argument fails with the usage block
"$BIN" > "$WORK/n.out" 2>&1 && rc=0 || rc=$?
check "pbsim no-args exit status" "$([ "$rc" -ne 0 ] && echo nonzero || echo zero)" "nonzero"
check "pbsim no-args usage text" "$(grep -qF -- 'USAGE: pbsim' "$WORK/n.out" && echo 0 || echo 1)" 0 "$WORK/n.out"

# 5. an invalid --data-type value is rejected
"$BIN" --data-type BAD ref.fasta > "$WORK/d.out" 2>&1 || true
check "pbsim bad data-type diagnostic" "$(grep -qF -- 'Acceptable value is CLR or CCS' "$WORK/d.out" && echo 0 || echo 1)" 0 "$WORK/d.out"

echo "PBSIM_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
