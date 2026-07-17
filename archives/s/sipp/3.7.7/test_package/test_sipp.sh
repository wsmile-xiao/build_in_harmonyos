#!/usr/bin/env bash
set -euo pipefail

tmp_output="$(mktemp)"
trap 'rm -f "$tmp_output"' EXIT

set +e
sipp -v >"$tmp_output" 2>&1
rc=$?
set -e

if [ "$rc" -ne 99 ]; then
    echo "expected upstream informational exit code 99 from 'sipp -v', got $rc" >&2
    cat "$tmp_output" >&2
    exit 1
fi

if ! grep -qi "SIPp" "$tmp_output"; then
    echo "expected version/help output from 'sipp -v' to mention SIPp" >&2
    cat "$tmp_output" >&2
    exit 1
fi

if ! grep -qi "free software" "$tmp_output" \
    && ! grep -qi "license" "$tmp_output" \
    && ! grep -qi "author" "$tmp_output"; then
    echo "expected informational banner from 'sipp -v'" >&2
    cat "$tmp_output" >&2
    exit 1
fi
