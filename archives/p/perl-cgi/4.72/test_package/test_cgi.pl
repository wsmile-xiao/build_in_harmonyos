#!/usr/bin/env perl
# test_cgi.pl — consumer test source for perl-cgi 4.72 (L0c).
#
# REAL API check (R34) on the packaged CGI:
#   CGI->new + param (upstream t/ tests usage).
# Usage: test_cgi.pl <site-perl-dir>
use strict;
use warnings;

# @INC injection must happen at compile time (use CGI is compile-time) —
# shift @ARGV inside BEGIN so $site is available before `use CGI`.
BEGIN {
    my $site = shift @ARGV
        or die "usage: test_cgi.pl <site-perl-dir>\n";
    die "site-perl dir missing: $site\n" unless -d $site;
    unshift @INC, $site;
}

use CGI ();

# Set up a CGI environment (GET with query string)
$ENV{REQUEST_METHOD} = 'GET';
$ENV{QUERY_STRING}   = 'game=chess&game=checkers&weather=dull';

my $q = CGI->new;
die "CGI->new failed\n" unless $q;

# param: list context returns all values for a key
my @games = $q->param('game');
die "param list mismatch: @games\n"
    unless @games == 2 && $games[0] eq 'chess' && $games[1] eq 'checkers';

# param: scalar context returns first value
my $weather = $q->param('weather');
die "param scalar mismatch: $weather\n" unless $weather eq 'dull';

print "OK: perl-cgi 4.72 real API ok (CGI->new/param)\n";
exit 0;
