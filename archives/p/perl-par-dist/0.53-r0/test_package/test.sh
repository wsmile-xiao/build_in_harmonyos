#!/bin/sh
# test_package/test.sh — smoke test for perl-par-dist (PAR::Dist module)
# Tests that the installed PAR::Dist module can be loaded and parse_dist_name() works.
# Usage: test.sh <perl_lib_path>
set -eu

PERL_LIB="${1:-}"
PERL_OPTS=""
if [ -n "$PERL_LIB" ]; then
    PERL_OPTS="-I${PERL_LIB}"
fi

echo "[test] PAR::Dist module load + parse_dist_name"
perl ${PERL_OPTS} -e '
use PAR::Dist;
my $dist = PAR::Dist::parse_dist_name("PAR-Dist-0.53-i386-freebsd-5.8.0.par");
die "test failed: parse_dist_name returned undef" unless defined $dist;
print "PAR::Dist test OK\n";
' && echo "✅ PAR::Dist test passed" || {
    echo "❌ PAR::Dist test failed"
    exit 1
}
