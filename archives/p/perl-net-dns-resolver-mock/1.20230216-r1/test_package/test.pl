#!/usr/bin/env perl
use strict;
use warnings;
use Test::More tests => 2;

# Verify the module can be loaded
use_ok('Net::DNS::Resolver::Mock');

# Verify it can create a new instance
my $resolver = Net::DNS::Resolver::Mock->new();
isa_ok($resolver, 'Net::DNS::Resolver::Mock');

print "test perl-net-dns-resolver-mock 1.20230216-r1: OK\n";
