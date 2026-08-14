#!/bin/sh
# test_package/run_test.sh — Test runner for perl-stream-buffered
# Usage: run_test.sh <perl_lib_path>
set -eu

PERL_LIB="$1"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -n "${PERL5LIB:-}" ]; then
    export PERL5LIB="${PERL_LIB}:${PERL5LIB}"
else
    export PERL5LIB="${PERL_LIB}"
fi

perl "${SCRIPT_DIR}/test_stream_buffered.pl"
