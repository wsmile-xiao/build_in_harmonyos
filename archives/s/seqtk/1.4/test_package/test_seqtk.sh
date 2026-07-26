#!/bin/sh
set -eu
if (set -o pipefail) 2>/dev/null; then
    set -o pipefail
fi

binary=${1:?seqtk binary path is required}
if [ ! -f "$binary" ] || [ ! -x "$binary" ]; then
    printf 'seqtk binary is not executable: %s\n' "$binary" >&2
    exit 1
fi

input="$(mktemp "${TMPDIR:-.}/seqtk-test.XXXXXX")"
fasta="$(mktemp "${TMPDIR:-.}/seqtk-test.XXXXXX")"
sizes="$(mktemp "${TMPDIR:-.}/seqtk-test.XXXXXX")"
trap 'rm -f "$input" "$fasta" "$sizes"' EXIT HUP INT TERM

run_and_report() {
    label=$1
    output=$2
    shift 2
    set +e
    "$@" >"$output" 2>&1
    status=$?
    set -e
    if [ "$status" -ne 0 ]; then
        printf '%s failed with exit code %s\n' "$label" "$status" >&2
        printf '%s output:\n' "$label" >&2
        cat "$output" >&2
        return "$status"
    fi
}

assert_line() {
    expected=$1
    output=$2
    if ! grep -Fqx "$expected" "$output"; then
        printf 'assertion failed: expected line %s\n' "$expected" >&2
        printf 'actual output:\n' >&2
        cat "$output" >&2
        return 1
    fi
}

printf '%s\n' '@read1' 'ACGT' '+' 'IIII' > "$input"
run_and_report 'seqtk seq' "$fasta" "$binary" seq -a "$input"
run_and_report 'seqtk size' "$sizes" "$binary" size "$input"

assert_line '>read1' "$fasta"
assert_line 'ACGT' "$fasta"
# seqtk size reports the record count and total sequence length.
expected_size=$(awk 'NR % 4 == 2 { count++; total += length($0) } END { printf "%d\t%d\n", count, total }' "$input")
assert_line "$expected_size" "$sizes"
