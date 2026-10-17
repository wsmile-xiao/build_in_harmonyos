#!/data/service/hnp/bin/bash
# Run a real Logo program through the installed ucblogo executable.
set -eu

UCLBLOGO="${1:-}"
if [ -z "$UCLBLOGO" ] || [ ! -x "$UCLBLOGO" ]; then
    echo "FAIL: ucblogo executable not found: $UCLBLOGO" >&2
    exit 1
fi
echo "PASS 1/7: ucblogo executable is present"

PACKAGE_ROOT=$(CDPATH= cd -- "$(dirname "$UCLBLOGO")/.." && pwd)
SHARE_ROOT="$PACKAGE_ROOT/share/ucblogo"

for directory in logolib helpfiles csls; do
    if [ ! -d "$SHARE_ROOT/$directory" ]; then
        echo "FAIL: packaged $directory directory is missing" >&2
        exit 1
    fi
done
echo "PASS 2/7: logolib directory is present"
echo "PASS 3/7: helpfiles directory is present"
echo "PASS 4/7: csls directory is present"

if [ ! -s "$SHARE_ROOT/logolib/Messages" ]; then
    echo "FAIL: packaged Messages file is missing or empty" >&2
    exit 1
fi
echo "PASS 5/7: logolib/Messages is readable and non-empty"
export LOGOLIB="$SHARE_ROOT/logolib"
export LOGOHELP="$SHARE_ROOT/helpfiles"
export CSLS="$SHARE_ROOT/csls"

output=$(
    printf '%s\n' \
        'MAKE "ANSWER (SUM (PRODUCT 6 7) (DIFFERENCE 10 10))' \
        'PRINT :ANSWER' \
        'IFELSE EQUAL? :ANSWER 42 [PRINT [UCLBLOGO_CONSUMER_OK]] [PRINT [UCLBLOGO_CONSUMER_FAIL]]' \
        'BYE' \
        | "$UCLBLOGO" -
)

printf '%s\n' "$output"
printf '%s\n' "$output" | grep -Fx '42' >/dev/null
echo "PASS 6/7: Logo program printed 42"

printf '%s\n' "$output" | grep -Fx 'UCLBLOGO_CONSUMER_OK' >/dev/null
if printf '%s\n' "$output" | grep -F 'UCLBLOGO_CONSUMER_FAIL' >/dev/null; then
    echo "FAIL: Logo consumer program reported failure" >&2
    exit 1
fi
echo "PASS 7/7: Logo success marker present and failure marker absent"

echo "PASS: installed ucblogo passed 7/7 consumer checks"
