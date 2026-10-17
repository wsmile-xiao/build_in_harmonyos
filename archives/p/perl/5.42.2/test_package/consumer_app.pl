#!/usr/bin/env perl
use strict;
use warnings;

use Cwd qw(getcwd);
use Config;
use File::Spec;
use File::Temp qw(tempdir);
use Getopt::Long qw(GetOptions);

my $mode = "downstream";
GetOptions("mode=s" => \$mode) or die "usage: $0 [--mode NAME]\n";

my $tmpdir = tempdir(CLEANUP => 1);
my $payload = File::Spec->catfile($tmpdir, "payload.txt");
my $joined = File::Spec->catfile("alpha", "beta");

open my $out, ">", $payload or die "open($payload): $!";
print {$out} join("\n",
    "mode=$mode",
    "osname=$Config::Config{osname}",
    "archname=$Config::Config{archname}",
    "cwd=" . getcwd(),
    "joined=$joined",
    "",
);
close $out or die "close($payload): $!";

open my $in, "<", $payload or die "open($payload): $!";
my $text = do { local $/; <$in> };
close $in or die "close($payload): $!";

die "missing mode" unless index($text, "mode=$mode") >= 0;
die "missing osname" unless index($text, "osname=$Config::Config{osname}") >= 0;
die "missing archname" unless index($text, "archname=$Config::Config{archname}") >= 0;
die "missing path join" unless index($text, "joined=$joined") >= 0;

print "consumer app ok\n";
