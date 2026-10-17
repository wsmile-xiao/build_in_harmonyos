#!/usr/bin/env perl
# test_jsonpp.pl — consumer test source for perl-json-pp 4.18 (L0c).
#
# REAL API check (R34) on the packaged JSON::PP:
#   encode/decode round-trip (upstream t/ tests usage).
# Usage: test_jsonpp.pl <site-perl-dir>
use strict;
use warnings;

my $site = shift @ARGV
    or die "usage: test_jsonpp.pl <site-perl-dir>\n";
die "site-perl dir missing: $site\n" unless -d $site;
unshift @INC, $site;

require JSON::PP;

# decode: JSON text -> Perl structure
my $json = '{"name":"Tom","age":42,"tags":["a","b"]}';
my $data = JSON::PP->new->decode($json);
die "decode name mismatch: $data->{name}\n" unless $data->{name} eq 'Tom';
die "decode age mismatch: $data->{age}\n" unless $data->{age} == 42;
die "decode tags mismatch\n"
    unless @{$data->{tags}} == 2 && $data->{tags}[1] eq 'b';

# encode: Perl structure -> JSON text (round-trip)
my $out = JSON::PP->new->encode($data);
die "encode round-trip mismatch: $out\n"
    unless $out =~ /"name":"Tom"/ && $out =~ /"age":42/;

print "OK: perl-json-pp 4.18 real API ok (JSON::PP decode/encode)\n";
exit 0;
