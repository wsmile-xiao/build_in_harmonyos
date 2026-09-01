#!/bin/sh
# Smoke test for sha3sum: verify SHA-3-224 hash of empty input.
# SHA-3-224("") = 6b4e03423667dbb73b6e15454f0eb1abd4597f9a1b078e3f5b5a6bc7
# Usage: LD_LIBRARY_PATH=<libkeccak-libdir> ./test_sha3sum.sh <sha3sum-binary>

set -eu

SHA3SUM="${1:?usage: test_sha3sum.sh <sha3sum-path>}"
EXPECTED="6b4e03423667dbb73b6e15454f0eb1abd4597f9a1b078e3f5b5a6bc7"

output=$(printf "" | "$SHA3SUM" 2>/dev/null || true)
echo "$output" | grep -q "$EXPECTED" || {
    echo "FAIL: expected '$EXPECTED' in output, got: $output" >&2
    exit 1
}
echo "PASS: sha3sum smoke test OK"
