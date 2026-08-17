#!/usr/bin/env perl
# test_compare.pl — test_package test source for perl-number-compare
# Verifies Number::Compare module can be loaded and performs numeric comparisons.
# PERL5LIB must be set to the package lib directory by the caller (conanfile.py).
use strict;
use warnings;
use Number::Compare;

# Test 1: greater-than comparison
my $comp_gt = Number::Compare->new('>10');
die "Test failed: >10 should match 15" unless $comp_gt->(15);
die "Test failed: >10 should NOT match 5" if $comp_gt->(5);

# Test 2: less-than comparison
my $comp_lt = Number::Compare->new('<5');
die "Test failed: <5 should match 3" unless $comp_lt->(3);
die "Test failed: <5 should NOT match 10" if $comp_lt->(10);

# Test 3: bare number (equality)
my $comp_eq = Number::Compare->new('42');
die "Test failed: 42 should match 42" unless $comp_eq->(42);
die "Test failed: 42 should NOT match 41" if $comp_eq->(41);

# Test 4: greater-than-or-equal
my $comp_ge = Number::Compare->new('>=100');
die "Test failed: >=100 should match 100" unless $comp_ge->(100);
die "Test failed: >=100 should match 200" unless $comp_ge->(200);
die "Test failed: >=100 should NOT match 99" if $comp_ge->(99);

# Test 5: less-than-or-equal
my $comp_le = Number::Compare->new('<=50');
die "Test failed: <=50 should match 50" unless $comp_le->(50);
die "Test failed: <=50 should match 10" unless $comp_le->(10);
die "Test failed: <=50 should NOT match 51" if $comp_le->(51);

# Test 6: magnitude suffixes
my $comp_k = Number::Compare->new('>1k');
die "Test failed: >1k should match 1500" unless $comp_k->(1500);
die "Test failed: >1k should NOT match 500" if $comp_k->(500);

my $comp_m = Number::Compare->new('>1m');
die "Test failed: >1m should match 2000000" unless $comp_m->(2000000);

print "Number::Compare test: OK\n";
