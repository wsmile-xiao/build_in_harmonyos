#!/bin/sh
# test_package/test.sh — Shell wrapper for Perl functional test
# CI L0c requires a recognized test source file (.c/.cpp/.sh/.py)
# This wrapper invokes the Perl test script with proper environment.
# PERL5LIB is set dynamically by test_package/conanfile.py test() method.
set -eu

export PERL_PARAMS_UTIL_PP=1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec perl "$SCRIPT_DIR/test.pl"
