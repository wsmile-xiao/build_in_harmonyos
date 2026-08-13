#!/bin/sh
# test_package/run_test.sh — Test runner for perl-string-shellquote
# Usage: run_test.sh <perl_lib_path> [shell_quote_bin_path]
#
# Sets PERL5LIB and runs the Perl test suite, then optionally tests
# the shell-quote CLI tool.
set -euo pipefail

PERL_LIB="$1"
SHELL_QUOTE_BIN="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Set PERL5LIB so Perl can find the module
if [ -n "${PERL5LIB:-}" ]; then
    export PERL5LIB="${PERL_LIB}:${PERL5LIB}"
else
    export PERL5LIB="${PERL_LIB}"
fi

# Run the Perl test suite
perl "${SCRIPT_DIR}/test_shellquote.pl"

# Test the shell-quote CLI tool if available
if [ -n "${SHELL_QUOTE_BIN}" ] && [ -f "${SHELL_QUOTE_BIN}" ]; then
    perl "${SHELL_QUOTE_BIN}" hello world
fi
