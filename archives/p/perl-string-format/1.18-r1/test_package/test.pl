#!/usr/bin/env perl
# test_package/test.pl — L1 consumer test for perl-string-format
# Verifies String::Format module is installed and functional

use strict;
use warnings;
use Test::More tests => 5;

# Test 1: Module loads without errors
use_ok('String::Format');

# Test 2: Basic stringf substitution
my $result = stringf('I like %a and %b.', {a => 'apples', b => 'bananas'});
is($result, 'I like apples and bananas.', 'basic stringf substitution');

# Test 3: Missing key preserved as-is
$result = stringf('Hello, %x!', {n => 'World'});
is($result, 'Hello, %x!', 'missing key preserved');

# Test 4: Field width truncation
$result = stringf('%.3r', {r => 'truncated'});
is($result, 'tru', 'field width truncation');

# Test 5: stringfactory class method
my $formatter = String::Format->stringfactory({n => sub { 'factory' }});
$result = $formatter->('Built by %n');
is($result, 'Built by factory', 'stringfactory method');
