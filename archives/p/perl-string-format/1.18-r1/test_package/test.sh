#!/bin/sh
# test_package/test.sh — L1 consumer test wrapper for perl-string-format
# Runs Perl functional tests against the installed String::Format module
set -euo pipefail

# L2 smoke test: verify module loads
perl -MString::Format -e 'print "OK\n"'

# Functional test: verify stringf() works with basic formatting
perl -e '
use String::Format qw(stringf);
my $r = stringf(q{I like %a and %b.}, {a=>q{apples},b=>q{bananas}});
die qq{FAIL: got [$r]} unless $r eq q{I like apples and bananas.};
print qq{FUNCTIONAL_TEST_PASS\n};
'

# Run the Perl test suite if Test::More is available
if perl -MTest::More -e 1 2>/dev/null; then
    perl "$(dirname "$0")/test.pl"
fi
