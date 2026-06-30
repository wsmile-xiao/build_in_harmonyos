#!/usr/bin/env perl
use strict;
use warnings;
use Net::Domain::TLD qw(tld_exists tlds);

# L1 smoke test: verify module loads and TLD lookup works
my $pass = 0;
my $total = 0;

# Test 1: module loads and exports
$total++; $pass++ if defined &tld_exists;
$total++; $pass++ if defined &tlds;

# Test 2: common TLDs exist
for my $tld (qw(com net org edu gov mil int)) {
    $total++;
    $pass++ if tld_exists($tld);
}

# Test 3: ccTLDs exist
for my $tld (qw(us uk cn jp de fr ru ca au)) {
    $total++;
    $pass++ if tld_exists($tld);
}

# Test 4: invalid TLDs don't exist
for my $tld (qw(xxx_fake invalid_tld zzz_test)) {
    $total++;
    $pass++ unless tld_exists($tld);
}

# Test 5: tlds() returns non-empty list
$total++;
my @all_tlds = tlds();
$pass++ if @all_tlds > 100;

# Test 6: tlds('cc') returns ccTLDs
$total++;
my @cc_tlds = tlds('cc');
$pass++ if @cc_tlds > 50;

print "test perl-net-domain-tld 1.75-r0: $pass/$total OK\n";
die "FAILED: $pass/$total tests passed\n" if $pass != $total;
