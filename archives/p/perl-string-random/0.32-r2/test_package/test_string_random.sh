#!/bin/sh
# test_package/test_string_random.sh — smoke test for perl-string-random 0.32-r2
# Called by test_package/conanfile.py via self.run()
# PERL5LIB must be set by the caller (conanfile.py test() method)
set -eu

# Test 1: Load String::Random and check version
echo "[test] 1/4: Load String::Random and check version"
ver=$(perl -MString::Random -e 'print $String::Random::VERSION' 2>&1) || {
    echo "FAIL: String::Random load test failed: $ver"
    exit 1
}
if [ "$ver" != "0.32" ]; then
    echo "FAIL: Version mismatch: expected 0.32, got $ver"
    exit 1
fi
echo "PASS: String::Random v$ver loaded"

# Test 2: randpattern — generate random string from single-char pattern
echo "[test] 2/4: randpattern method"
perl <<'PERL' || { echo "FAIL: randpattern test failed"; exit 1; }
use strict;
use warnings;
use String::Random;

my $sr = String::Random->new();
my $s = $sr->randpattern("Ccnc");
die "randpattern: wrong length" unless length($s) == 4;
die "randpattern: no uppercase" unless $s =~ /^[A-Z]/;
die "randpattern: no lowercase" unless $s =~ /[a-z]/;
die "randpattern: no digit" unless $s =~ /\d/;
print "randpattern OK";
PERL
echo "PASS: randpattern test"

# Test 3: randregex — generate random string from regex pattern
echo "[test] 3/4: randregex method"
perl <<'PERL' || { echo "FAIL: randregex test failed"; exit 1; }
use strict;
use warnings;
use String::Random;

my $sr = String::Random->new();
my $s = $sr->randregex("\\d{6}");
die "randregex: wrong length" unless length($s) == 6;
die "randregex: not all digits" unless $s =~ /^\d{6}$/;
print "randregex OK";
PERL
echo "PASS: randregex test"

# Test 4: random_string — generate random string with default pattern
echo "[test] 4/4: random_string method"
perl <<'PERL' || { echo "FAIL: random_string test failed"; exit 1; }
use strict;
use warnings;
use String::Random;

my $s = String::Random::random_string("Ccnc");
die "random_string: wrong length" unless defined($s) && length($s) == 4;
print "random_string OK";
PERL
echo "PASS: random_string test"

echo "All 4 tests passed."
