#!/bin/sh
set -euo pipefail
# Shell wrapper for perl-strictures test_package
# Sets PERL5LIB and runs the Perl test script
LIB_DIR="${1:?LIB_DIR is required}"
export PERL5LIB="$LIB_DIR"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
perl "$SCRIPT_DIR/test_strictures.pl"
