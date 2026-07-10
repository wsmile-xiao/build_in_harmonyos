#!/bin/sh
# Smoke test wrapper for SQL::Abstract
# Environment: PERL (perl binary path), PERL5LIB (module paths)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Find perl interpreter (check env, then known OHOS locations, then PATH)
if [ -n "$PERL" ] && [ -x "$PERL" ]; then
    PERL_BIN="$PERL"
else
    PERL_BIN=""
    for p in /data/service/hnp/bin/perl /usr/bin/perl /usr/local/bin/perl; do
        if [ -x "$p" ]; then
            PERL_BIN="$p"
            break
        fi
    done
    if [ -z "$PERL_BIN" ]; then
        PERL_BIN="perl"
    fi
fi

# Source Conan run environment if available (sets PERL5LIB from package_info)
if [ -f "$SCRIPT_DIR/conanrun.sh" ]; then
    . "$SCRIPT_DIR/conanrun.sh"
fi

# Get Perl's default @INC and merge with PERL5LIB
PERL_INC=$("$PERL_BIN" -e 'print join(":", @INC)' 2>/dev/null)
if [ -n "$PERL5LIB" ]; then
    export PERL5LIB="$PERL5LIB:$PERL_INC"
else
    export PERL5LIB="$PERL_INC"
fi

"$PERL_BIN" "$SCRIPT_DIR/smoke_test.pl"
