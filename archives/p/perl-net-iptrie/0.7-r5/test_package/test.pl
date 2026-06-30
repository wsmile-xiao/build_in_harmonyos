#!/usr/bin/env perl
use strict;
use warnings;
use Net::IPTrie;

# L1 smoke test: verify module loads and IP trie operations work
my $pass = 0;
my $total = 0;

# Test 1: module loads and constructor works
$total++;
my $tr;
eval { $tr = Net::IPTrie->new(version => 4); };
$pass++ unless $@;

# Test 2: add an IPv4 address
$total++;
eval { $tr->add(address => '10.0.0.0', prefix => 8); };
$pass++ unless $@;

# Test 3: add a host address with data
$total++;
eval { $tr->add(address => '10.0.0.1', data => 'test_data'); };
$pass++ unless $@;

# Test 4: find an existing address
$total++;
my $found;
eval { $found = $tr->find(address => '10.0.0.1'); };
$pass++ if $found && !$@;

# Test 5: find closest parent for non-existent address
$total++;
eval { $found = $tr->find(address => '10.0.0.2'); };
$pass++ if $found && $found->address eq '10.0.0.0' && !$@;

# Test 6: create IPv6 trie
$total++;
my $tr6;
eval { $tr6 = Net::IPTrie->new(version => 6); };
$pass++ unless $@;

# Test 7: add IPv6 address
$total++;
eval { $tr6->add(address => '2001:db8::', prefix => 32); };
$pass++ unless $@;

# Test 8: traverse the trie
$total++;
my $count = 0;
eval { $count = $tr->traverse(code => sub { $count++; }); };
$pass++ if defined $count && $count > 0 && !$@;

print "test perl-net-iptrie 0.7-r5: $pass/$total OK\n";
die "FAILED: $pass/$total tests passed\n" if $pass != $total;
