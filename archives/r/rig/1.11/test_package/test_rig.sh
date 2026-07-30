#!/bin/sh
# Exercise deterministic consumer scenarios derived from the upstream rig.6 manpage.

set -eu

RIG_BIN="${1:-}"
DATA_DIR="${2:-}"

fail()
{
    echo "ERROR: $1"
    exit 1
}

if [ -z "$RIG_BIN" ] || [ -z "$DATA_DIR" ]; then
    fail "rig binary path and data directory are required"
fi

if [ ! -x "$RIG_BIN" ]; then
    fail "$RIG_BIN not found or not executable"
fi

for name in fnames.idx lnames.idx locdata.idx mnames.idx street.idx; do
    if [ ! -f "$DATA_DIR/$name" ]; then
        fail "missing data file $DATA_DIR/$name"
    fi
done

test_output_file="${TMPDIR:-/tmp}/rig-test-$$.out"
trap 'rm -f "$test_output_file"' 0 HUP INT TERM

assert_name_in_set()
{
    candidate_name="$1"
    expected_set="$2"

    case "$expected_set" in
        female)
            sed 's/\r$//' "$DATA_DIR/fnames.idx" |
                grep -Fx "$candidate_name" >/dev/null
            ;;
        male)
            sed 's/\r$//' "$DATA_DIR/mnames.idx" |
                grep -Fx "$candidate_name" >/dev/null
            ;;
        both)
            sed 's/\r$//' "$DATA_DIR/fnames.idx" |
                grep -Fx "$candidate_name" >/dev/null ||
                sed 's/\r$//' "$DATA_DIR/mnames.idx" |
                grep -Fx "$candidate_name" >/dev/null
            ;;
        *)
            fail "unknown expected name set: $expected_set"
            ;;
    esac
}

validate_output()
{
    check_output="$1"
    expected_identities="$2"
    expected_name_set="$3"

    printf "%s\n" "$check_output" >"$test_output_file"
    non_empty_lines=$(sed '/^$/d' "$test_output_file" | wc -l |
        sed 's/[[:space:]]//g')
    expected_lines=$((expected_identities * 4))
    if [ "$non_empty_lines" -ne "$expected_lines" ]; then
        fail "expected $expected_lines non-empty lines, got $non_empty_lines"
    fi

    identity_index=1
    while [ "$identity_index" -le "$expected_identities" ]; do
        first_line_number=$(((identity_index - 1) * 5 + 1))
        street_line_number=$((first_line_number + 1))
        location_line_number=$((first_line_number + 2))
        phone_line_number=$((first_line_number + 3))

        identity_line=$(sed -n "${first_line_number}p" "$test_output_file")
        street_line=$(sed -n "${street_line_number}p" "$test_output_file")
        location_line=$(sed -n "${location_line_number}p" "$test_output_file")
        phone_line=$(sed -n "${phone_line_number}p" "$test_output_file")

        if ! printf "%s\n" "$identity_line" |
            grep -Eq '^[A-Za-z][A-Za-z .'\''-]+ [A-Za-z][A-Za-z .'\''-]+$'; then
            fail "identity $identity_index has an invalid name: $identity_line"
        fi
        if ! printf "%s\n" "$street_line" | grep -Eq '^[0-9]+ .+'; then
            fail "identity $identity_index has an invalid street: $street_line"
        fi
        if ! printf "%s\n" "$location_line" | grep -Eq ', [A-Z]{2}  [0-9]{5}$'; then
            fail "identity $identity_index has an invalid location: $location_line"
        fi
        if ! printf "%s\n" "$phone_line" | grep -Eq '^\([0-9]{3}\) xxx-xxxx$'; then
            fail "identity $identity_index has an invalid phone: $phone_line"
        fi

        first_name=${identity_line%% *}
        if ! assert_name_in_set "$first_name" "$expected_name_set"; then
            fail "identity $identity_index uses an unexpected first name: $first_name"
        fi

        identity_index=$((identity_index + 1))
    done
}

passed_cases=0

case_output=$("$RIG_BIN" -d "$DATA_DIR")
validate_output "$case_output" 1 both
passed_cases=$((passed_cases + 1))
echo "PASS [A1]: default mode generated one identity"

case_output=$("$RIG_BIN" -d "$DATA_DIR" -c 3)
validate_output "$case_output" 3 both
passed_cases=$((passed_cases + 1))
echo "PASS [A2]: -c generated the requested identity count"

case_output=$("$RIG_BIN" -d "$DATA_DIR" -f -c 10)
validate_output "$case_output" 10 female
passed_cases=$((passed_cases + 1))
echo "PASS [A3]: -f generated identities from the female name data"

case_output=$("$RIG_BIN" -d "$DATA_DIR" -m -c 10)
validate_output "$case_output" 10 male
passed_cases=$((passed_cases + 1))
echo "PASS [A4]: -m generated identities from the male name data"

case_output=$("$RIG_BIN" -d "$DATA_DIR" -f -m -c 10)
validate_output "$case_output" 10 both
passed_cases=$((passed_cases + 1))
echo "PASS [A5]: combined -f/-m mode accepted both name data sets"

if [ "$passed_cases" -ne 5 ]; then
    fail "expected 5 added consumer scenarios, got $passed_cases"
fi

echo "PASS: 5/5 added consumer scenarios passed"
