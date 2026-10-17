#!/usr/bin/env sh
# test_flameshot.sh — L1 smoke test for the packaged flameshot CLI.
#
# R34: the test must exercise the packaged binary. We invoke
# `flameshot --version` and assert the output contains "Flameshot".
#
# This script is a static source artifact for the L0c gate (which scans
# for test_package/test* source files). The actual Conan L1 test runner
# is test_package/conanfile.py's test() method; this file documents and
# mirrors the same assertion for review and can be run standalone.
set -eu

: "${FLAMESHOT_BIN:=flameshot}"

# --version does not open a window, safe on headless workers.
version_out="$("$FLAMESHOT_BIN" --version)"
case "$version_out" in
    *Flameshot*)
        echo "PASS: flameshot --version → $version_out"
        exit 0
        ;;
    *)
        echo "FAIL: flameshot --version did not mention Flameshot (got: $version_out)" >&2
        exit 1
        ;;
esac
