use Net::NTP;
my $v = $Net::NTP::VERSION;
die "version mismatch: got $v" unless $v eq "1.5";
print "OK: Net::NTP v$v
";
