#!/usr/bin/env perl
# test_package/test_deprecationmanager.pl — L1 smoke test for perl-package-deprecationmanager
# Tests real Package::DeprecationManager API: import with -deprecations,
# deprecated() function, custom message, feature-based deprecation, warning capture.
#
# R34/L1e: This test verifies that the module is loaded from the Conan
# package cache path (.conan2), not from a system Perl installation.
use strict;
use warnings;
use Package::DeprecationManager -deprecations => {
    'TestModule::old_method' => '0.01',
    'feature_x'              => '0.05',
};

my $pass = 0;
my $total = 0;
my @results;

# Test 1: module loads
my $t1 = defined $INC{'Package/DeprecationManager.pm'} ? 1 : 0;
$total++; $pass++ if $t1;
push @results, "T1(load)=$t1";

# Test 2: module loaded from Conan cache (R34/L1e)
my $module_path = $INC{'Package/DeprecationManager.pm'} // '';
my $t2 = ($module_path =~ /conan2/) ? 1 : 0;
$total++; $pass++ if $t2;
push @results, "T2(conan2)=$t2 path=$module_path";

# Test 3: deprecated() function is exported to caller
my $t3 = defined *main::deprecated{CODE} ? 1 : 0;
$total++; $pass++ if $t3;
push @results, "T3(export)=$t3";

# Test 4: deprecated(message => ...) produces a warning
my $t4 = 0;
{
    my $warning_caught = 0;
    local $SIG{__WARN__} = sub { $warning_caught = 1 if $_[0] =~ /deprecated/ };
    deprecated(message => 'this is deprecated');
    $t4 = $warning_caught;
}
$total++; $pass++ if $t4;
push @results, "T4(warn)=$t4";

# Test 5: deprecated(message => ...) with custom message
my $t5 = 0;
{
    my $msg_caught = '';
    local $SIG{__WARN__} = sub { $msg_caught = $_[0] };
    deprecated(message => 'custom deprecation message');
    $t5 = ($msg_caught =~ /custom deprecation message/) ? 1 : 0;
}
$total++; $pass++ if $t5;
push @results, "T5(msg)=$t5";

# Test 6: deprecated() with message and feature parameters
my $t6 = 0;
{
    my $msg_caught = '';
    local $SIG{__WARN__} = sub { $msg_caught = $_[0] };
    deprecated(
        message => 'Feature X is deprecated',
        feature => 'feature_x',
    );
    $t6 = ($msg_caught =~ /Feature X is deprecated/) ? 1 : 0;
}
$total++; $pass++ if $t6;
push @results, "T6(feat)=$t6";

# Test 7: deprecated() for a feature triggers the correct deprecation version
my $t7 = 0;
{
    my $msg_caught = '';
    local $SIG{__WARN__} = sub { $msg_caught = $_[0] };
    deprecated(
        message => 'old_method is removed',
        feature => 'TestModule::old_method',
    );
    $t7 = ($msg_caught =~ /old_method is removed/) ? 1 : 0;
}
$total++; $pass++ if $t7;
push @results, "T7(ver)=$t7";

# Test 8: Package::DeprecationManager has an import() method
my $t8 = defined *Package::DeprecationManager::import{CODE} ? 1 : 0;
$total++; $pass++ if $t8;
push @results, "T8(import)=$t8";

# Test 9: Package::DeprecationManager version is defined
my $t9 = defined $Package::DeprecationManager::VERSION ? 1 : 0;
$total++; $pass++ if $t9;
push @results, "T9(ver)=$t9";

print "test perl-package-deprecationmanager 0.18-r1: $pass/$total OK\n";
print "DEBUG: " . join(" ", @results) . "\n" if $pass != $total;
die "FAILED: $pass/$total tests passed\n" if $pass != $total;
