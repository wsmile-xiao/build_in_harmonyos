#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for otp 1.2.2 (installed bin/otp).
#
# Really runs the installed binary and checks deterministic output and the
# MD5 signature file against known-good values (the generator is fully
# deterministic when seeded with -r).
#
# Env: OTP_BIN = path to the installed otp executable
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

BIN="${OTP_BIN:-otp}"
WORK="${TMPDIR:-.}/otp-consumer.$$"
umask 000
mkdir -p "$WORK" || { echo "FAIL: cannot create workdir $WORK"; exit 1; }
trap 'rm -rf "$WORK"' EXIT

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

trim() { printf '%s' "$1" | sed 's/[[:space:]]*$//'; }

# 1. usage banner
got=$("$BIN" -U 2>&1 | head -n 1)
check "otp -U prints the generator banner" "$got" "otp  --  One-time pad generator."

# 2. deterministic lowercase-letter keys with a fixed seed
got=$(trim "$("$BIN" -rTEST -n4)")
check "otp -rTEST -n4 deterministic keys" "$got" \
	"1) gtwe-uzpy  2) chog-inzx  3) moum-mmqd  4) tscc-jgwq"

# 3. deterministic MD5 signature file
"$BIN" -rTEST -n4 -m"$WORK/t1.md5" >/dev/null
got=$(head -n 1 "$WORK/t1.md5")
check "otp -m writes a deterministic MD5 signature" "$got" \
	"04AE0013DFAC7807A4846425AAE03D48"

# 4. deterministic digit keys
got=$(trim "$("$BIN" -rTEST -n7 -d4)")
check "otp -rTEST -n7 -d4 deterministic digits" "$got" \
	"1) 0782  2) 0790  3) 8982  4) 2559  5) 6806  6) 8809  7) 9046"

echo "OTP_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
