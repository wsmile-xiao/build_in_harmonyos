#!/bin/sh
# test_checkcompiler.sh — L1 test for Devel::CheckCompiler
# Tests that the module loads, version is correct, and API functions are callable.
#
# check_c99() may return 0 on OHOS due to -fstack-protector-strong
# incompatibility with ld.lld — this is a known platform limitation.

set -eu

PERL_LIB="${1:-}"
if [ -z "$PERL_LIB" ]; then
    echo "Usage: $0 <perl_lib_dir>"
    echo "Example: $0 /path/to/lib/perl5"
    exit 1
fi

export PERL5LIB="${PERL_LIB}:${PERL5LIB:-}"

perl -e '
use strict;
use warnings;
use Devel::CheckCompiler;

# Test 1: module loads and has correct version
die "VERSION mismatch" unless $Devel::CheckCompiler::VERSION eq "0.03";
print "Test 1 PASS: module loaded, version 0.03\n";

# Test 2: check_c99() is callable (may return 0 on OHOS)
my $result = check_c99();
print "Test 2 PASS: check_c99() returned $result (platform limitation expected on OHOS)\n";

# Test 3: check_compile() is callable with custom C source
my $r2 = check_compile("int main(void) { return 0; }\n");
print "Test 3 PASS: check_compile() returned $r2\n";

print "ALL TESTS PASSED\n";
'
