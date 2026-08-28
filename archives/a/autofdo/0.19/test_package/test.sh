#!/bin/sh
# Smoke test for autofdo OHOS build.
#
# The autofdo tools use gflags: `--help` prints usage and exits 1 (normal
# gflags behavior), so we verify the program starts and prints its flags
# rather than checking the exit code.
set -e

out=$(create_gcov --help 2>&1) || true
if echo "$out" | grep -q "Flags from create_gcov.cc"; then
    echo "create_gcov: OK"
else
    echo "create_gcov: FAILED to print usage" >&2
    exit 1
fi
