#!/usr/bin/env bash
set -eu

# Invoke the packaged binary by the absolute path passed by Conan's test()
# method. Moving bin/ in the destructive negative test then proves the test
# depends on the packaged artifact rather than a system executable.
ABNFGEN="${1:-abnfgen}"
if [ -z "$ABNFGEN" ] || { [ ! -x "$ABNFGEN" ] && [ "$ABNFGEN" != "abnfgen" ]; }; then
    echo "abnfgen binary not found: $ABNFGEN" >&2
    exit 127
fi

workdir="${TMPDIR:-$PWD}/abnfgen-test-$$"
trap 'rm -rf "$workdir"' EXIT
mkdir -p "$workdir"

cat > "$workdir/grammar.abnf" <<'GRAMMAR'
token = 1*3%x78.79 CRLF
GRAMMAR

# Parse and validate the ABNF grammar.
"$ABNFGEN" -l "$workdir/grammar.abnf"

# Generate three samples to a directory.
"$ABNFGEN" -d "$workdir/output" -n 3 "$workdir/grammar.abnf"

# Assert exactly three files and grammar-conforming content.
count=$(find "$workdir/output" -type f | wc -l | tr -d '[:space:]')
[ "$count" = "3" ]

for sample in "$workdir"/output/*; do
    value=$(tr -d '\r\n' < "$sample")
    case "$value" in
        xy|xyxy|xyxyxy) ;;
        *) echo "invalid generated sample: $value" >&2; exit 1 ;;
    esac
done

echo "abnfgen functional assertions passed"
