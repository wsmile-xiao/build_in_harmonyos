#!/bin/sh
# test_package/run_tests.sh — Perl test runner wrapper for CI L0c recognition
# Runs the consumer-perspective test for Specio::Library::Path::Tiny 0.05
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

export SPECIO_IMPLEMENTATION=PP

perl "$SCRIPT_DIR/test_specio_library_path_tiny.pl" && perl "$SCRIPT_DIR/functional_test.pl"
