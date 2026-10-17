#!/bin/sh
# test_package/run_test.sh — Test runner for perl-file-remove 1.61
# Usage: run_test.sh <perl_lib_path>
#
# Sets PERL5LIB to the packaged File/Remove.pm directory and runs the
# real consumer test (temp tree create -> remove()/rm() -> assert gone).
set -euo pipefail

PERL_LIB="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -n "${PERL5LIB:-}" ]; then
    export PERL5LIB="${PERL_LIB}:${PERL5LIB}"
else
    export PERL5LIB="${PERL_LIB}"
fi

perl "${SCRIPT_DIR}/test_remove.pl"
