#!/usr/bin/perl
# Consumer test for the packaged ceni 2.33 Ceni::Backend module.
# Exercises the real interfaces-file parser (no mocks, no stubs).
use strict;
use warnings;

use File::Temp qw(tempfile);
use Test::More tests => 6;

use_ok('Ceni::Backend');

my ($fh, $filename) = tempfile(UNLINK => 1);
print $fh <<'ENI';
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet static
	address 192.168.1.10
	netmask 255.255.255.0
	gateway 192.168.1.1
ENI
close $fh;

my $bend = Ceni::Backend->new({ file => $filename });
ok(defined $bend, 'Ceni::Backend->new returned an object');
ok($bend->parse_eni(), 'parse_eni parsed the temporary interfaces file');

my $eth0 = $bend->get_iface_conf('eth0');
is($eth0->{method}, 'static', 'eth0 method is static');
is($eth0->{stanza}{address}, '192.168.1.10', 'eth0 address parsed');

ok($bend->is_iface_configured('eth0'), 'eth0 is reported as configured');
