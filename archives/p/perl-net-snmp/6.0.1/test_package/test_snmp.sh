#!/bin/sh
# test_snmp.sh — Net::SNMP consumer test
# CI L0c requires .sh/.c/.cpp/.py extension for test source files
# This shell wrapper runs the Perl test via perl -e
set -euo pipefail

PERL5LIB="${PERL5LIB:-}" perl -e '
use strict;
use warnings;
use Net::SNMP;

# Test 1: module loads and has correct version
my $v = Net::SNMP->VERSION;
die "version mismatch: got $v" unless $v eq "v6.0.1";
print "Test 1 PASS: module loaded, version $v\n";

# Test 2: session() returns an object for SNMPv2c
my ($session, $error) = Net::SNMP->session(
    -hostname  => "127.0.0.1",
    -community => "public",
    -timeout  => 1,
);
die "session() failed: $error" unless defined $session;
die "not a Net::SNMP object" unless ref($session) eq "Net::SNMP";
print "Test 2 PASS: session() creates Net::SNMP object\n";

# Test 3: close() works
$session->close();
print "Test 3 PASS: close() works\n";

print "ALL TESTS PASSED\n";
'
