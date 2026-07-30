#!/usr/bin/env bash
# R34: Test must actually exercise the tested package's binary
# git-crypt is a CLI tool — test by running git-crypt --version
# Using bash shebang for POSIX-compatible pipefail support (CS-R7)
set -euo pipefail

GIT_CRYPT_BIN="${1:-git-crypt}"
output="$("$GIT_CRYPT_BIN" --version 2>&1)"

# Verify the binary produces expected version output
case "$output" in
    *git-crypt*0.8.0*)
        echo "PASS: git-crypt binary works correctly"
        echo "  output: $output"
        exit 0
        ;;
    *)
        echo "FAIL: unexpected output from git-crypt --version"
        echo "  output: $output"
        exit 1
        ;;
esac
