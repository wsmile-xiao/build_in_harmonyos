#!/bin/bash
# test_params_util.sh — L1 test for perl-params-util (Params::Util)
# Tests that the installed module files exist and core functions work
# in pure Perl fallback mode (PERL_PARAMS_UTIL_PP=1).
set -eu

PKG_FOLDER="${1:?Usage: test_params_util.sh <pkg_folder>}"

# Dynamically locate site_perl arch directory by finding Util.pm
UTIL_PM="$(find "$PKG_FOLDER" -path "*/Params/Util.pm" -type f -print -quit)"
if [ -z "$UTIL_PM" ]; then
    echo "FAIL: Params/Util.pm not found in package" >&2
    exit 1
fi
SITE_ARCH="$(dirname "$(dirname "$UTIL_PM")")"

# Check expected files exist
for f in \
    "$SITE_ARCH/Params/Util.pm" \
    "$SITE_ARCH/Params/Util/PP.pm" \
    "$SITE_ARCH/auto/Params/Util/Util.so"; do
    if [ ! -f "$f" ]; then
        echo "FAIL: Expected file not found: $f" >&2
        exit 1
    fi
    echo "Found: $f"
done

# Test module loading and core functions (pure Perl fallback)
export PERL5LIB="$SITE_ARCH"
export PERL_PARAMS_UTIL_PP=1

perl -e '
use Params::Util;
my $v = $Params::Util::VERSION;
print "version: $v\n";
my $s = defined Params::Util::_STRING("hello") ? "pass" : "fail";
print "_STRING: $s\n";
my $n = defined Params::Util::_NUMBER(42) ? "pass" : "fail";
print "_NUMBER: $n\n";
die "_STRING test failed" unless $s eq "pass";
die "_NUMBER test failed" unless $n eq "pass";
'

echo "ALL TESTS PASSED"
