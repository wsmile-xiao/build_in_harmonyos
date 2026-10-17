#!/usr/bin/env bash
#--------------------------------------------------------------------
# Consumer test for lexd 1.3.5 (the installed bin/lexd).
#
# R34: every check below runs the real delivered binary on real lexicon
# data; nothing is echoed or stubbed. A missing/empty binary or a stub
# that produces no transducer fails here (that is also what makes the
# CI L1e sabotage check meaningful).
#
# Env:
#   LEXD_BIN      path to the installed lexd executable (required)
#   LEXD_DATA     directory holding the upstream fixtures (required)
#   LEXD_RUNNER   optional prefix used to execute foreign-arch binaries
#                 ("qemu-aarch64" when validating the OHOS cross build
#                 from an x86 host); empty on a native OHOS worker.
#   LEXD_RESULT   file to write the machine-readable summary into
#--------------------------------------------------------------------
set -euo pipefail

BIN="${LEXD_BIN:?LEXD_BIN must point to the installed lexd executable}"
DATA="${LEXD_DATA:?LEXD_DATA must point to the upstream fixture directory}"
RESULT="${LEXD_RESULT:-}"
RUNNER="${LEXD_RUNNER:-}"

# Never scratch inside the archive tree: for an explicit test package the CWD
# is the recipe folder, and the CI junk check rejects runtime residue there.
WORK=$(mktemp -d "${TMPDIR:-/tmp}/lexd-consumer-XXXXXX")
trap 'rm -rf "$WORK"' EXIT

CHECKS=0
FAILS=0

check() { # check <name> <actual> <expected>
	CHECKS=$((CHECKS + 1))
	if [ "$2" = "$3" ]; then
		echo "PASS: $1"
	else
		echo "FAIL: $1 (got '$2', want '$3')"
		FAILS=$((FAILS + 1))
	fi
}

lexd() { # lexd <args...>
	if [ -n "$RUNNER" ]; then
		# shellcheck disable=SC2086
		$RUNNER "$BIN" "$@"
	else
		"$BIN" "$@"
	fi
}

# 0. the delivered artifact must exist and be executable
if [ ! -x "$BIN" ]; then
	echo "FAIL: lexd binary not found or not executable: $BIN"
	exit 1
fi
check "installed lexd binary is executable" "yes" "yes"

# 1. --version reports the packaged upstream version
VERSION_OUT=$(lexd --version 2>&1)
echo "$VERSION_OUT"
case "$VERSION_OUT" in
*1.3.5*) check "lexd --version reports 1.3.5" "1.3.5" "1.3.5" ;;
*) check "lexd --version reports 1.3.5" "$VERSION_OUT" "1.3.5" ;;
esac

# 2. --help prints the usage banner
HELP_OUT=$(lexd --help 2>&1 || true)
case "$HELP_OUT" in
*"USAGE: lexd"*) check "lexd --help prints usage" "usage" "usage" ;;
*) check "lexd --help prints usage" "$HELP_OUT" "USAGE: lexd ..." ;;
esac

# 3. upstream negative case 1: column 0 in a pattern header is rejected
set +e
NEG1=$(lexd "$DATA/negtest-col0.lexd" 2>&1 >/dev/null)
NEG1_RC=$?
set -e
check "negtest-col0.lexd is rejected (exit 1)" "$NEG1_RC" "1"
case "$NEG1" in
*"Invalid column number"*) check "negtest-col0 error message" "msg" "msg" ;;
*) check "negtest-col0 error message" "$NEG1" "Invalid column number ..." ;;
esac

# 4. upstream negative case 2: unbalanced bracket is rejected
set +e
NEG2=$(lexd "$DATA/negtest-trailing-bracket.lexd" 2>&1 >/dev/null)
NEG2_RC=$?
set -e
check "negtest-trailing-bracket.lexd is rejected (exit 1)" "$NEG2_RC" "1"
case "$NEG2" in
*"Unexpected closing bracket"*) check "negtest-trailing-bracket error message" "msg" "msg" ;;
*) check "negtest-trailing-bracket error message" "$NEG2" "Unexpected closing bracket ..." ;;
esac

# 5. a real lexicon compiles to a real ATT transducer whose accepted surface
#    forms are exactly the upstream expectations (36 fixtures x 6 flag
#    variants = 216 combinations / 798 gold assertions; replaces the upstream
#    hfst-txt2fst|hfst-fst2strings oracle, see att_check.py for the rationale).
ATT_RESULT="$WORK/att_result.txt"
if python3 "$(dirname "$0")/att_check.py" "$BIN" "$DATA" "$ATT_RESULT"; then
	CHECKS=$((CHECKS + 1))
	GOLD_CHECKS=$(sed -n 's/^GOLD_CHECKS=//p' "$ATT_RESULT")
	GOLD_COMBOS=$(sed -n 's/^GOLD_COMBOS=//p' "$ATT_RESULT")
	echo "PASS: upstream gold verification (${GOLD_CHECKS:-?} assertions / ${GOLD_COMBOS:-?} combinations)"
else
	CHECKS=$((CHECKS + 1))
	FAILS=$((FAILS + 1))
	echo "FAIL: upstream gold verification"
fi

# 6. HarmonyOS-specific: the delivered artifact is an OHOS aarch64 ELF
#    (e_ident magic 7f454c46, EI_CLASS=2 -> ELF64, EI_DATA=1 -> little endian,
#    e_type=0x0003 ET_DYN, e_machine=0x00b7 AArch64) and it actually executes
#    on the OHOS target, which every check above and the gold verification
#    already demonstrate.
ELF_HDR=$(od -An -tx1 -N20 "$BIN" | tr -d ' \n')
check "delivered binary is ELF64 AArch64 (OHOS aarch64)" \
	"$ELF_HDR" "7f454c460201010000000000000000000300b700"

# 7. writing to an explicit output file must yield the same transducer as
#    stdout (exercises lexd's ICU file-output path on OHOS).
set +e
lexd "$DATA/test-opt.lexd" "$WORK/opt.att" >/dev/null 2>"$WORK/ofile.err"
OFILE_RC=$?
lexd "$DATA/test-opt.lexd" > "$WORK/opt.stdout.att" 2>/dev/null
set -e
check "lexd writes the output file (rc 0)" "$OFILE_RC" "0"
if [ -s "$WORK/opt.att" ] && cmp -s "$WORK/opt.att" "$WORK/opt.stdout.att"; then
	check "output file transducer equals stdout transducer" "same" "same"
else
	check "output file transducer equals stdout transducer" \
		"$(wc -c < "$WORK/opt.att" 2>/dev/null || echo 0) bytes / $(wc -c < "$WORK/opt.stdout.att" 2>/dev/null || echo 0) bytes" \
		"equal"
fi

# 8. missing input file must fail gracefully (no crash / signal)
set +e
lexd "$WORK/does-not-exist.lexd" >/dev/null 2>&1
MISS_RC=$?
set -e
if [ "$MISS_RC" -ge 128 ]; then
	check "missing input does not crash (exit<128)" "$MISS_RC" "<128"
else
	check "missing input does not crash (exit<128)" "ok" "ok"
fi

echo "LEXD_CHECK_SUMMARY checks=$CHECKS fails=$FAILS"
if [ -n "$RESULT" ]; then
	{
		echo "CHECKS=$CHECKS"
		echo "FAILS=$FAILS"
		echo "GOLD_CHECKS=${GOLD_CHECKS:-0}"
		echo "GOLD_COMBOS=${GOLD_COMBOS:-0}"
	} > "$RESULT"
fi
[ "$FAILS" -eq 0 ]
