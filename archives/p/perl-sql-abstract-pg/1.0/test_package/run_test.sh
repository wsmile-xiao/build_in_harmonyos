#!/bin/sh
# run_test.sh — Shell wrapper for SQL::Abstract::Pg test suite
# Satisfies CI L0c (test source file in test_package/)
# Calls test_sql_abstract_pg.pl which contains the actual Perl tests
# Usage: sh run_test.sh <pkg_lib_dir> [dep_lib_dir ...]
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Build PERL5LIB from all provided lib dirs
PERL5LIB=""
for dir in "$@"; do
    if [ -n "$dir" ] && [ -d "$dir" ]; then
        if [ -z "$PERL5LIB" ]; then
            PERL5LIB="$dir"
        else
            PERL5LIB="$PERL5LIB:$dir"
        fi
    fi
done
if [ -n "$PERL5LIB" ]; then
    export PERL5LIB="${PERL5LIB}:${PERL5LIB_ENV:-}"
fi

exec perl "$SCRIPT_DIR/test_sql_abstract_pg.pl"
