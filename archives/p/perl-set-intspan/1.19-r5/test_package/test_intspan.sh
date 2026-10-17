#!/bin/sh
# Test that Set::IntSpan Perl module is properly installed.
# CI L0c: recognized as test source file (.sh extension).
# Uses double quotes in Perl print so \n is interpolated as newline.
perl -e '
use Set::IntSpan;
my $set = Set::IntSpan->new("1-10,20-25");
die "cardinality mismatch" unless $set->cardinality() == 16;
die "member check failed" unless $set->member(5);
die "non-member check failed" if $set->member(15);
print "Set::IntSpan test OK\n";
'
