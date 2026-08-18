#!/usr/bin/env perl
# test_package/test_stash.pl — L1 smoke test for perl-package-stash
# Tests real Package::Stash API: new, add_symbol, get_symbol, has_symbol,
# remove_symbol, list_all_symbols, get_all_symbols, name, namespace.
use strict;
use warnings;
use Package::Stash;

# Verify Package::Stash is loaded from conan cache, not system Perl (R34/L1e)
# Ensures test genuinely depends on the conan package, not a system install
my $stash_path = $INC{'Package/Stash.pm'} // '';
die "Package::Stash not loaded from conan cache: $stash_path\n"
    unless $stash_path =~ m{conan};

my $pass = 0;
my $total = 0;

# Test 1: module loads
$total++; $pass++ if defined $INC{'Package/Stash.pm'};

# Test 2: create a stash
my $stash = Package::Stash->new('Test::Pkg');
$total++; $pass++ if defined $stash;

# Test 3: stash name
$total++; $pass++ if $stash->name eq 'Test::Pkg';

# Test 4: namespace
$total++; $pass++ if defined $stash->namespace;

# Test 5: add and check scalar symbol
$stash->add_symbol('$scalar_var', 42);
$total++; $pass++ if $stash->has_symbol('$scalar_var');

# Test 6: get scalar symbol
my $val = $stash->get_symbol('$scalar_var');
$total++; $pass++ if defined $val && $$val == 42;

# Test 7: add and check array symbol
$stash->add_symbol('@array_var', [1, 2, 3]);
$total++; $pass++ if $stash->has_symbol('@array_var');

# Test 8: get array symbol
my $arr = $stash->get_symbol('@array_var');
$total++; $pass++ if defined $arr && @$arr == 3;

# Test 9: add and check hash symbol
$stash->add_symbol('%hash_var', {a => 1, b => 2});
$total++; $pass++ if $stash->has_symbol('%hash_var');

# Test 10: get hash symbol
my $hash = $stash->get_symbol('%hash_var');
$total++; $pass++ if defined $hash && keys %$hash == 2;

# Test 11: add code symbol
$stash->add_symbol('&code_var', sub { return 'hello' });
$total++; $pass++ if $stash->has_symbol('&code_var');

# Test 12: remove scalar symbol
$stash->remove_symbol('$scalar_var');
$total++; $pass++ unless $stash->has_symbol('$scalar_var');

# Test 13: list_all_symbols returns ARRAY keys
my @arrays = $stash->list_all_symbols('ARRAY');
$total++; $pass++ if grep { $_ eq 'array_var' } @arrays;

# Test 14: get_all_symbols returns HASH
my $hashes = $stash->get_all_symbols('HASH');
$total++; $pass++ if ref($hashes) eq 'HASH' && exists $hashes->{'hash_var'};

# Test 15: verify code symbol persists after operations
$total++; $pass++ if $stash->has_symbol('&code_var');

print "test perl-package-stash 0.40-r1: $pass/$total OK\n";
die "FAILED: $pass/$total tests passed\n" if $pass != $total;
