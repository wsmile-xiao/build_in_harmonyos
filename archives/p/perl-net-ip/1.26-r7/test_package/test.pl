#!/usr/bin/env perl
use strict;
use warnings;
use Net::IP qw(ip_compress_address ip_expand_address ip_get_version ip_iptobin ip_bintoip ip_is_ipv4 ip_is_ipv6);

# L1 smoke test: verify module loads and IP functions work
my $pass = 0;
my $total = 0;

# Test 1: module loads and exports
$total++; $pass++ if defined &ip_compress_address;
$total++; $pass++ if defined &ip_expand_address;
$total++; $pass++ if defined &ip_get_version;

# Test 2: IPv4 address version detection
$total++; $pass++ if ip_get_version('192.168.1.1') eq '4';
$total++; $pass++ if ip_get_version('10.0.0.1') eq '4';

# Test 3: IPv6 address version detection
$total++; $pass++ if ip_get_version('::1') eq '6';
$total++; $pass++ if ip_get_version('2001:db8::1') eq '6';

# Test 4: IPv4 validation
$total++; $pass++ if ip_is_ipv4('192.168.1.1');
$total++; $pass++ if !ip_is_ipv4('not_an_ip');

# Test 5: IPv6 validation
$total++; $pass++ if ip_is_ipv6('2001:db8::1');
$total++; $pass++ if !ip_is_ipv6('192.168.1.1');

# Test 6: IPv6 address compression
$total++; $pass++ if ip_compress_address('2001:0db8:0000:0000:0000:0000:0000:0001', 6) eq '2001:db8::1';

# Test 7: IPv6 address expansion
$total++; $pass++ if ip_expand_address('2001:db8::1', 6) eq '2001:0db8:0000:0000:0000:0000:0000:0001';

# Test 8: IPv4 to binary conversion
my $bin = ip_iptobin('192.168.1.1', 4);
$total++; $pass++ if defined $bin && length($bin) == 32;

# Test 9: binary to IPv4 conversion
$total++; $pass++ if ip_bintoip(ip_iptobin('10.0.0.1', 4), 4) eq '10.0.0.1';

print "test perl-net-ip 1.26-r7: $pass/$total OK\n";
die "FAILED: $pass/$total tests passed\n" if $pass != $total;
