#!/usr/bin/env bash
set -euo pipefail

tmp_output="$(mktemp)"
trap 'rm -f "$tmp_output"' EXIT

set +e
sipp -v >"$tmp_output" 2>&1
rc=$?
set -e

grep -q "SIPp 3.7.7" "$tmp_output"
grep -q "This program is free software" "$tmp_output"

if [ "$rc" -ne 99 ]; then
    echo "expected upstream informational exit code 99 from 'sipp -v', got $rc" >&2
    cat "$tmp_output" >&2
    exit 1
fi
