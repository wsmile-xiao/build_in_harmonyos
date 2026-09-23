#!/usr/bin/env bash
# Consumer behavior checks for the real cpipe executable.
set -euo pipefail

bin="${1:?usage: test_cpipe_native.sh /absolute/path/to/cpipe}"
if [ ! -x "$bin" ]; then
  echo "cpipe binary is missing or not executable: $bin" >&2
  exit 1
fi

work="$(mktemp -d "$PWD/cpipe-test.XXXXXX")"
trap 'rm -rf "$work"' EXIT

# A missing/non-greedy read path would drop or alter this embedded-NUL payload.
printf 'cpipe-pass-through\nline-2\000tail' >"$work/input"
"$bin" -ngr <"$work/input" >"$work/output" 2>"$work/stderr"
cmp "$work/input" "$work/output"

# A broken buffer-size option would fail to preserve the same payload.
"$bin" -b 1 -ngr <"$work/input" >"$work/output-buffered" 2>"$work/stderr-buffered"
cmp "$work/input" "$work/output-buffered"

# Throughput output belongs on stderr and must not contaminate stdout.
"$bin" -vt <"$work/input" >"$work/output-verbose" 2>"$work/stderr-verbose"
cmp "$work/input" "$work/output-verbose"
grep -q 'thru:' "$work/stderr-verbose"

# An unknown option must be rejected with a diagnostic.
if "$bin" --definitely-invalid >"$work/invalid-out" 2>"$work/invalid-err"; then
  echo "invalid option unexpectedly succeeded" >&2
  exit 1
fi
grep -q 'unknown option' "$work/invalid-err"

echo "CPIPE_NATIVE_TEST_OK cases=4"
