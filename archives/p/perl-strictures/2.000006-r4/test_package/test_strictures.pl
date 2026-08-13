#!/usr/bin/env perl
# Test script for perl-strictures test_package
# Verifies that strictures module can be loaded, imported, and basic functionality works
use strict;
use warnings;

my $ok = 1;

# Test 1: Module loads
eval { require strictures };
if ($@) {
    print "FAIL: cannot load strictures: $@\n";
    $ok = 0;
} else {
    print "PASS: strictures module loaded\n";
}

# Test 2: Version check
if (defined $strictures::VERSION && $strictures::VERSION =~ /^2\./) {
    print "PASS: strictures version is $strictures::VERSION\n";
} else {
    print "FAIL: unexpected strictures version\n";
    $ok = 0;
}

# Test 3: strictures import works (enables strict + fatal warnings)
eval { strictures->import };
if ($@) {
    print "FAIL: strictures->import failed: $@\n";
    $ok = 0;
} else {
    print "PASS: strictures->import succeeded\n";
}

# Test 4: strictures::extra loads
eval { require strictures::extra };
if ($@) {
    print "SKIP: strictures::extra not available: $@\n";
} else {
    print "PASS: strictures::extra loaded\n";
}

exit($ok ? 0 : 1);
