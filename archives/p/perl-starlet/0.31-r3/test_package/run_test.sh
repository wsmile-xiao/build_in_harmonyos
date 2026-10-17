#!/bin/sh
# test_package/run_test.sh — Test runner for perl-starlet
# Usage: run_test.sh <perl_lib_path>
#
# Uses perl -I to add the module path (PERL5LIB env var may be
# disabled by taint mode or platform security policy on OHOS).
set -eu

PERL_LIB="$1"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Use -I flag for reliable @INC path injection across all Perl builds
perl -I"${PERL_LIB}" "${SCRIPT_DIR}/test_starlet.pl"
