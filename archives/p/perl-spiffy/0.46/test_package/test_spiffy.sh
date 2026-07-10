#!/bin/sh
# test_package/test_spiffy.sh — smoke test for perl-spiffy 0.46
# Called by test_package/conanfile.py via self.run()
# PERL5LIB must be set by the caller (conanfile.py test() method)
set -eu

# Test 1: Load Spiffy and check version
echo "[test] 1/6: Load Spiffy and check version"
ver=$(perl -MSpiffy -e 'print Spiffy->VERSION' 2>&1) || {
    echo "FAIL: Spiffy load test failed: $ver"
    exit 1
}
if [ "$ver" != "0.46" ]; then
    echo "FAIL: Version mismatch: expected 0.46, got $ver"
    exit 1
fi
echo "PASS: Spiffy v$ver loaded"

# Test 2: Spiffy 'field' declaration with default values and setter
echo "[test] 2/6: Spiffy field declaration"
perl <<'PERL' || { echo "FAIL: field test failed"; exit 1; }
use Spiffy;
package MyTest;
use Spiffy -base;
field foo => 42;
field bar => 99;
package main;
my $obj = MyTest->new;
die "field foo failed" unless $obj->foo == 42;
die "field bar failed" unless $obj->bar == 99;
$obj->foo(100);
die "field setter failed" unless $obj->foo == 100;
print "field OK";
PERL
echo "PASS: field test"

# Test 3: Spiffy 'const' declaration
echo "[test] 3/6: Spiffy const declaration"
perl <<'PERL' || { echo "FAIL: const test failed"; exit 1; }
use Spiffy;
package MyConst;
use Spiffy -base;
const PI => 3.14159;
package main;
die "const PI failed" unless MyConst->PI == 3.14159;
print "const OK";
PERL
echo "PASS: const test"

# Test 4: Spiffy 'mixin' functionality
echo "[test] 4/6: Spiffy mixin functionality"
perl <<'PERL' || { echo "FAIL: mixin test failed"; exit 1; }
use Spiffy;
package MyMixin;
use Spiffy -base;
sub hello { return "mixin-hello" }
package MyUser;
use Spiffy -base;
use mixin 'MyMixin';
package main;
my $obj = MyUser->new;
die "mixin failed" unless $obj->hello eq "mixin-hello";
print "mixin OK";
PERL
echo "PASS: mixin test"

# Test 5: Spiffy 'super' method
echo "[test] 5/6: Spiffy super method"
perl <<'PERL' || { echo "FAIL: super test failed"; exit 1; }
use Spiffy;
package Parent;
use Spiffy -base;
sub greet { return "parent" }
package Child;
use base 'Parent';
sub greet { return super() . "+child" }
package main;
my $obj = Child->new;
my $result = $obj->greet;
die "super failed: got '$result'" unless $result eq "parent+child";
print "super OK";
PERL
echo "PASS: super test"

# Test 6: Spiffy export mechanism — verify -base exports field/const/stub
echo "[test] 6/6: Spiffy export mechanism"
perl <<'PERL' || { echo "FAIL: export test failed"; exit 1; }
use Spiffy;
package MyExport;
use Spiffy -base;
die "export field failed" unless defined &MyExport::field;
die "export const failed" unless defined &MyExport::const;
die "export stub failed" unless defined &MyExport::stub;
package main;
print "export OK";
PERL
echo "PASS: export test"

echo "All 6 tests passed."
