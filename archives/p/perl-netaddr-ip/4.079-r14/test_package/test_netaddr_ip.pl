#!/usr/bin/env perl
# test_netaddr_ip.pl — NetAddr::IP XS module functional test
# Verifies: Perl XS module loading + IPv4/IPv6 address operations + XS mode verification
# Called by test_package/conanfile.py test() method with PERL5LIB set to the package lib dir.
use strict;
use warnings;

# Remove system site_perl from @INC to avoid broken Socket6 module.
# NetAddr::IP::Util is designed to work without Socket6 (falls back to
# standard gethostbyname). The system Socket6 is broken on HarmonyOS.
BEGIN {
    @INC = grep { $_ !~ /site_perl/ } @INC;
}

use NetAddr::IP;

# Basic IPv4 test
my $ip = NetAddr::IP->new('192.168.1.1/24');
die "Failed to create IPv4 address" unless $ip;
die "Bad address: $ip" unless "$ip" eq '192.168.1.1/24';

# Basic IPv6 test
my $ip6 = NetAddr::IP->new('::1/128');
die "Failed to create IPv6 address" unless $ip6;

# Test XS module is loaded (not pure Perl)
use NetAddr::IP::Util_IS;
die "XS module should not be pure Perl" if NetAddr::IP::Util_IS->pure();

print "OK: NetAddr::IP XS module loaded and working\n";
