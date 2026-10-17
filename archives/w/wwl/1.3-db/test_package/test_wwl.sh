#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for wwl 1.3-db (installed wwl / locator programs).
#
# Uses the worked examples from the upstream wwl(1) man page.
#
# Env:
#   WWL_BIN      path to the installed wwl executable
#   LOCATOR_BIN  path to the installed locator executable
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

WWL="${WWL_BIN:?WWL_BIN must point to the installed wwl executable}"
LOCATOR="${LOCATOR_BIN:?LOCATOR_BIN must point to the installed locator executable}"

WORK="${TMPDIR:-.}/wwl-test.$$"
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

check_line() { # check_line <name> <file> <expected-line>
	check "$1" "$(grep -F -x -- "$3" "$2" || true)" "$3"
}

# 1. wwl(1) example: fn25di -> jo55ei
"$WWL" fn25di jo55ei > "$WORK/q1.txt" 2>&1 || true
check_line "wwl fn25di jo55ei distance/azimuth" "$WORK/q1.txt" \
	"qrb: 5810 kilometers, azimuth: 46 degrees"

# 2. wwl(1) example: jo55 -> ec41 (short locators auto-fill AA)
"$WWL" jo55 ec41 > "$WORK/q2.txt" 2>&1 || true
check_line "wwl jo55 ec41 distance/azimuth" "$WORK/q2.txt" \
	"qrb: 15996 kilometers, azimuth: 216 degrees"

# 3. locator(1) example: FN25di
"$LOCATOR" FN25di > "$WORK/l1.txt" 2>&1 || true
check_line "locator FN25di locator name" "$WORK/l1.txt" "Locator    : FN25DI"
check_line "locator FN25di coordinates" "$WORK/l1.txt" \
	"Coordinates: Long: (W) -75.75 Lat : (N) 45.3333"

# 4. locator(1) example: jo55ei
"$LOCATOR" jo55ei > "$WORK/l2.txt" 2>&1 || true
check_line "locator jo55ei coordinates" "$WORK/l2.txt" \
	"Coordinates: Long: (E) 10.33 Lat : (N) 55.3333"

# 5. locator(1) example: ec41 (short locator auto-fills AA)
"$LOCATOR" ec41 > "$WORK/l3.txt" 2>&1 || true
check_line "locator ec41 locator name" "$WORK/l3.txt" "Locator    : EC41AA"
check_line "locator ec41 coordinates" "$WORK/l3.txt" \
	"Coordinates: Long: (W) -92.00 Lat : (S) -69.0000"

# 6. no arguments -> failure with a usage banner
"$WWL" > "$WORK/usage.txt" 2>&1 && rc=0 || rc=$?
check "wwl without arguments exits non-zero" "$([ "$rc" -ne 0 ] && echo 0 || echo 1)" 0
check "wwl without arguments prints usage" "$(grep -c -F 'home_locator' "$WORK/usage.txt")" 1

# 7. invalid locator -> failure with a diagnostic
"$WWL" zz99 zz99 > "$WORK/bad.out" 2> "$WORK/bad.err" && rc=0 || rc=$?
check "wwl rejects an invalid locator" "$([ "$rc" -ne 0 ] && echo 0 || echo 1)" 0

echo "WWL_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
