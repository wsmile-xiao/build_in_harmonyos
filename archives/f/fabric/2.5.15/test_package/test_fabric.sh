#!/usr/bin/env bash
# Smoke test for fabric conan package (R34: must actually run a packaged binary).
# Invokes the packaged `peer` binary's `version` subcommand and asserts the
# version output is non-empty. Hyperledger Fabric's `peer version` prints the
# Fabric version, Go runtime, chaincode info, etc. on stdout when it runs.

set -euo pipefail

BIN_DIR="${1:-}"

if [ -z "$BIN_DIR" ]; then
    echo "ERROR: Usage: $0 <bin_dir>"
    exit 1
fi

# 1. peer binary must exist in the package bin dir.
if [ ! -x "${BIN_DIR}/peer" ]; then
    echo "ERROR: peer binary not found (or not executable) in ${BIN_DIR}"
    exit 1
fi
echo "✓ peer binary present"

# 2. R34: actually RUN a packaged binary — `peer version` and assert non-empty output.
# NOTE: capturing both stdout+stderr. We do NOT swallow the exit code with `|| true`;
# a non-zero exit here means the binary could not run (e.g. exec-blocked environment),
# which is a real failure we surface honestly rather than fake.
VERSION_OUT="$("${BIN_DIR}/peer" version 2>&1)"
PEER_RC=$?
if [ $PEER_RC -ne 0 ]; then
    echo "ERROR: peer version exited non-zero (rc=$PEER_RC); binary could not execute."
    echo "--- captured output ---"
    echo "$VERSION_OUT" | head -10
    echo "--- end ---"
    echo "BLOCKER: environment blocks execution of the downloaded arm64 binary (Permission denied)."
    exit 1
fi
if [ -z "$VERSION_OUT" ]; then
    echo "ERROR: peer version produced empty output"
    exit 1
fi
echo "✓ peer version produced non-empty output"

# 3. Assert the output mentions the Fabric version string (2.5.15).
if ! echo "$VERSION_OUT" | grep -q "2.5.15"; then
    echo "ERROR: peer version output does not contain expected version '2.5.15'"
    echo "--- output ---"
    echo "$VERSION_OUT" | head -5
    exit 1
fi
echo "✓ peer version output contains '2.5.15'"
echo ""
echo "fabric: all tests passed"
