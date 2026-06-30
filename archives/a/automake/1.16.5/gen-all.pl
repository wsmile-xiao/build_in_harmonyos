#!/usr/bin/perl
use strict;
use warnings;
use File::Copy;

my $home = $ENV{HOME} || '/storage/Users/currentUser';
my $prefix = "$home/usr/local";
my $pkg = 'automake';
my $ver = '1.16.5';
my $api = '1.16';
my $perl_path = '/bin/env perl';

my %vars = (
  '@PERL@'              => $perl_path,
  '@SHELL@'             => '/bin/sh',
  '@VERSION@'           => $ver,
  '@PACKAGE@'           => $pkg,
  '@PACKAGE_VERSION@'   => $ver,
  '@PACKAGE_BUGREPORT@' => 'bug-automake@gnu.org',
  '@RELEASE_YEAR@'      => '2021',
  '@APIVERSION@'        => $api,
  '@datadir@'           => "$prefix/share",
  '@pkgvdatadir@'       => "$prefix/share/$pkg-$api",
  '@amdir@'             => "$prefix/share/$pkg-$api/am",
  '@bindir@'            => "$prefix/bin",
  '@scriptdir@'         => "$prefix/share/$pkg-$api",
  '@automake_acdir@'    => "$prefix/share/aclocal-$api",
  '@system_acdir@'      => "$prefix/share/aclocal",
  '@docdir@'            => "$prefix/share/doc/$pkg",
  '@libdir@'            => "$prefix/lib",
);

sub subst_file {
  my ($infile, $outfile, $script_name) = @_;
  open my $in, '<', $infile or die "Cannot open $infile: $!";
  open my $out, '>', $outfile or die "Cannot open $outfile: $!";
  my $line_num = 0;
  while (<$in>) {
    $line_num++;
    if ($line_num == 1 && /^#!.*perl/) {
      s|^#!.*perl.*|#!/bin/env perl|;
    }
    if (defined $script_name) {
      s|\@configure_input\@|Generated from $infile; do not edit by hand.|;
    }
    for my $k (keys %vars) {
      my $v = $vars{$k};
      s|\Q$k\E|$v|g;
    }
    print $out $_;
  }
  close $in;
  close $out;
  print "  Generated $outfile\n";
}

# 1. Generate Config.pm
subst_file('lib/Automake/Config.in', 'lib/Automake/Config.pm', undef);

# 2. Generate amversion.m4 (if .in exists)
if (-f 'm4/amversion.in') {
  subst_file('m4/amversion.in', 'm4/amversion.m4', undef);
}

# 3. Generate bin/automake and bin/aclocal
for my $script (qw(automake aclocal)) {
  subst_file("bin/$script.in", "bin/$script", $script);
  chmod 0755, "bin/$script";
}

# 4. Create versioned symlinks
symlink('automake', 'bin/automake-1.16') unless -e 'bin/automake-1.16';
symlink('aclocal', 'bin/aclocal-1.16') unless -e 'bin/aclocal-1.16';

print "All files generated successfully.\n";
