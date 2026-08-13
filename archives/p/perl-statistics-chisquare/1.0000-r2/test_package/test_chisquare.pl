#!/usr/bin/env perl
# test_package/test_chisquare.pl — Functional test for Statistics::ChiSquare
# Run via: perl -I<lib_dir> test_chisquare.pl
use strict;
use warnings;

my $pass = 0;
my $fail = 0;

# Test 1: Module loads
eval { require Statistics::ChiSquare; };
if ($@) {
    print "FAIL: Cannot load Statistics::ChiSquare: $@\n";
    $fail++;
} else {
    $pass++;
}

# Test 2: chisquare() returns a defined result
my $result;
eval {
    $result = Statistics::ChiSquare::chisquare(500, 500);
};
if ($@) {
    print "FAIL: chisquare() threw exception: $@\n";
    $fail++;
} elsif (!defined $result) {
    print "FAIL: chisquare() returned undef\n";
    $fail++;
} else {
    $pass++;
}

# Test 3: Result is a non-empty string
if (defined $result && length($result) > 0) {
    $pass++;
} else {
    print "FAIL: chisquare() returned empty result\n";
    $fail++;
}

if ($fail == 0) {
    print "PASS: All $pass tests passed\n";
} else {
    print "FAIL: $fail tests failed\n";
}
exit($fail > 0 ? 1 : 0);
