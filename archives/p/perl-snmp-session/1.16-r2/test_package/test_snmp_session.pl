use strict;
use warnings;
use SNMP_Session;
use BER;
use SNMP_util;
my $version = $SNMP_Session::VERSION;
die 'version mismatch' unless $version eq '1.16';
# Test BER encode (no network needed)
my $encoded = encode_oid(1,3,6,1);
die 'BER encode failed' unless defined $encoded && length($encoded) > 0;
print "SNMP::Session test OK\n";
