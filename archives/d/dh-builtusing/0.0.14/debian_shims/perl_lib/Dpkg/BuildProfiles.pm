package Dpkg::BuildProfiles;
use strict;
use warnings;
use Exporter 'import';
our @EXPORT_OK = qw(get_build_profiles);

sub get_build_profiles {
    my $v = $ENV{DEB_BUILD_PROFILES} // '';
    my @p = split /[\s,]+/, $v;
    @p = grep { length $_ } @p;
    return @p;
}

1;
