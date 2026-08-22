#!/bin/bash
# cryptokit 1.21.1 API smoke test - SHA-256 functional verification
set -euo pipefail

TEST_DIR="$(dirname "$0")"
echo "=== cryptokit 1.21.1 SHA-256 API test ==="

# Build and run the test if compiled binary exists
if [ -f ./test_cryptokit ]; then
    ./test_cryptokit
    echo "=== cryptokit API test PASSED ==="
elif [ -f "${TEST_DIR}/test_cryptokit" ]; then
    "${TEST_DIR}/test_cryptokit"
    echo "=== cryptokit API test PASSED ==="
else
    echo "ERROR: test_cryptokit binary not found — test cannot run!" >&2
    exit 1
fi
