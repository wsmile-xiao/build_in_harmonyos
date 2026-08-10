#!/bin/sh
set -eu

conf_file="${PWD}/sample-appconfig.conf"
printf '%s\n' 'mode = fast' 'retry = 3' > "$conf_file"

perl -Mstrict -Mwarnings -MAppConfig=:argcount -e '
my $file = shift @ARGV;
my $cfg = AppConfig->new(
    { GLOBAL => { ARGCOUNT => ARGCOUNT_ONE } },
    "mode",
    "retry",
    "verbose" => { ARGCOUNT => ARGCOUNT_NONE },
);
$cfg->file($file);
my @argv = qw(--mode slow --verbose);
$cfg->args(\@argv);
die "mode parse failed\n" unless $cfg->mode eq "slow";
die "retry parse failed\n" unless $cfg->retry == 3;
die "flag parse failed\n" unless $cfg->verbose;
print "AppConfig consumer test OK\n";
' "$conf_file"
