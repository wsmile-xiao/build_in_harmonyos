#!/usr/bin/env perl
# test_timepiece.pl — consumer test source for perl-time-piece 1.41 (L0c).
#
# REAL API check (R34) on the packaged Time::Piece:
#   localtime/strptime + strftime/epoch (upstream t/ tests usage).
# Usage: test_timepiece.pl <site-perl-dir>
use strict;
use warnings;

# @INC injection must happen at compile time (use Time::Piece is
# compile-time) — shift @ARGV inside BEGIN so $site is available before
# `use Time::Piece` (AI review: runtime unshift → core-module false pass)
BEGIN {
    my $site = shift @ARGV
        or die "usage: test_timepiece.pl <site-perl-dir>\n";
    die "site-perl dir missing: $site\n" unless -d $site;
    unshift @INC, $site;
}

use Time::Piece;

# localtime: current time object
my $t = localtime;
die "localtime year mismatch\n" unless $t->year >= 2020;

# strptime: parse a formatted time string
my $tp = Time::Piece->strptime('2026-08-17 12:30', '%Y-%m-%d %H:%M');
die "strptime year mismatch: " . $tp->year . "\n" unless $tp->year == 2026;
die "strptime mon mismatch: " . $tp->mon . "\n" unless $tp->mon == 8;
die "strptime mday mismatch: " . $tp->mday . "\n" unless $tp->mday == 17;

# strftime: format back (round-trip)
my $out = $tp->strftime('%Y-%m-%d');
die "strftime round-trip mismatch: $out\n" unless $out eq '2026-08-17';

print "OK: perl-time-piece 1.41 real API ok (localtime/strptime/strftime)\n";
exit 0;
