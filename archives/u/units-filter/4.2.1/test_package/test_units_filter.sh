#!/bin/sh
# test_units_filter.sh <binary> <workdir>
# Consumer smoke test for the packaged units-filter binary.
# Feeds physical-quantity expressions on stdin and checks the SI value
# (first output field). Ends with a deterministic trailer:
#   RESULT: <P> passed, <F> failed
# which test_package/conanfile.py parses for HMBS_TEST_PACKAGE_RESULT.
set -u
BIN="$1"
WORKDIR="${2:-.}"
mkdir -p "$WORKDIR"
TMPOUT="$WORKDIR/case.out"

PASS=0
FAIL=0

check() {
    desc="$1"
    input="$2"
    want="$3"
    if printf '%s\n' "$input" | "$BIN" > "$TMPOUT" 2>&1; then
        got_first="$(awk '{print $1}' "$TMPOUT" | head -n 1)"
    else
        got_first=""
    fi
    if [ -z "$got_first" ]; then
        echo "FAIL  $desc: empty output (input: $input)"
        FAIL=$((FAIL + 1))
        return
    fi
    case "$got_first" in
        *"$want"*)
            echo "PASS  $desc: '$input' -> '$got_first'"
            PASS=$((PASS + 1))
            ;;
        *)
            echo "FAIL  $desc: '$input' -> '$got_first' (want substring '$want')"
            FAIL=$((FAIL + 1))
            ;;
    esac
}

# 1: base length unit
check "meter" "1 m" "1"
# 2: kilo prefix conversion to SI
check "kilometer" "1 km" "1000"
# 3: hour to seconds
check "hour" "1 h" "3600"
# 4: cubic centimetre to cubic metre
check "cubic-cm" "1 cm^3" "1e-06"
# 5: gram to kilogram base
check "gram" "1 g" "0.001"
# 6: compound torque growth-rate expression from upstream README
check "torque-rate" "1.5e3 nN.m.s^-1" "1.5e-06"

# 7 (negative control): an invalid expression must NOT produce a numeric
# first field; it must be rejected so the harness proves it can fail.
# NOTE: units-filter prints "ERROR at ..." to stdout and exit(1) on parse
# errors (vendored/src/unitesparser.cc: printf("ERROR ..."); exit(1)), so
# the output file must be read regardless of exit status. The previous
# `if pipeline; then read; else first=""` form discarded the ERROR line
# exactly when the binary correctly rejected the input (exit 1 -> first=""),
# turning a correct rejection into "not rejected (got '')".
printf '%s\n' '!!!not-a-unit!!!' | "$BIN" > "$TMPOUT" 2>&1
first="$(awk '{print $1}' "$TMPOUT" | head -n 1)"
case "$first" in
    ERROR*)
        echo "PASS  negative-control: invalid expression rejected ('$first')"
        PASS=$((PASS + 1))
        ;;
    *)
        echo "FAIL  negative-control: invalid expression not rejected (got '$first')"
        FAIL=$((FAIL + 1))
        ;;
esac

echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
