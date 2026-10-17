#!/usr/bin/env perl
# test_uri.pl — consumer test source for perl-uri 5.35 (L0c).
#
# REAL API check (R34) on the packaged URI:
#   URI->new + scheme/host/port/path accessors (upstream t/ tests usage).
# Usage: test_uri.pl <site-perl-dir>
use strict;
use warnings;

# @INC injection must happen at compile time (use URI is compile-time) —
# shift @ARGV inside BEGIN so $site is available before `use URI`
# (AI review: runtime unshift → core-module false pass)
BEGIN {
    my $site = shift @ARGV
        or die "usage: test_uri.pl <site-perl-dir>\n";
    die "site-perl dir missing: $site\n" unless -d $site;
    unshift @INC, $site;
}

use URI;

my $u = URI->new('http://user@example.com:8080/path/to?q=1#frag');
die "scheme mismatch: " . $u->scheme . "\n" unless $u->scheme eq 'http';
die "host mismatch: " . $u->host . "\n" unless $u->host eq 'example.com';
die "port mismatch: " . $u->port . "\n" unless $u->port == 8080;
die "path mismatch: " . $u->path . "\n" unless $u->path eq '/path/to';

print "OK: perl-uri 5.35 real API ok (URI->new/scheme/host/port/path)\n";
exit 0;
