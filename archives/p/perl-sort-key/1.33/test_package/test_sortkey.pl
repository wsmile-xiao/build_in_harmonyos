#!/usr/bin/env perl
use strict;
use warnings;
use Sort::Key qw(keysort nkeysort rnkeysort nsort rnsort
                 ikeysort rikeysort ukeysort rukeysort
                 usort rusort nkeysort_inplace);
sub ri_keysort (&@);

# Test 1: module loads and has correct version
my $version = $Sort::Key::VERSION;
die 'VERSION not defined' unless defined $version;
die 'VERSION mismatch' unless $version eq '1.33';
print "Test 1 PASS: module loaded, version $version\n";

# Test 2: keysort sorts strings
my @data = qw(foo bar baz qux alpha beta gamma delta);
my @sorted = keysort { $_ } @data;
my @expected = sort @data;
die 'keysort string failed' unless "@sorted" eq "@expected";
print "Test 2 PASS: keysort sorts strings correctly\n";

# Test 3: nkeysort sorts numerically
@data = map { rand(200) - 100 } 1..1000;
@sorted = nkeysort { $_ } @data;
@expected = sort { $a <=> $b } @data;
die 'nkeysort failed' unless "@sorted" eq "@expected";
print "Test 3 PASS: nkeysort sorts numerically\n";

# Test 4: rnkeysort reverse numeric sort
@sorted = rnkeysort { $_ } @data;
@expected = reverse sort { $a <=> $b } @data;
die 'rnkeysort failed' unless "@sorted" eq "@expected";
print "Test 4 PASS: rnkeysort reverse numeric sort\n";

# Test 5: nsort and rnsort
die 'nsort failed' unless "@{[nsort @data]}" eq "@{[sort { $a <=> $b } @data]}";
die 'rnsort failed' unless "@{[rnsort @data]}" eq "@{[reverse sort { $a <=> $b } @data]}";
print "Test 5 PASS: nsort and rnsort work\n";

# Test 6: ikeysort and rikeysort (integer sort)
my @idata = map { int(rand(2**16) - 2**15) } 1..1000;
die 'ikeysort failed' unless "@{[ikeysort { $_ } @idata]}" eq "@{[sort { $a <=> $b } @idata]}";
die 'rikeysort failed' unless "@{[rikeysort { $_ } @idata]}" eq "@{[sort { $b <=> $a } @idata]}";
print "Test 6 PASS: ikeysort and rikeysort (integer sort)\n";

# Test 7: nkeysort with key function (squared)
@data = map { rand(200) - 100 } 1..1000;
@sorted = nkeysort { $_ * $_ } @data;
@expected = sort { $a*$a <=> $b*$b } @data;
die 'nkeysort squared failed' unless "@sorted" eq "@expected";
print "Test 7 PASS: nkeysort with key function works\n";

# Test 8: nkeysort_inplace modifies array in place
my @inplace = map { rand(200) - 100 } 1..500;
my @copy = @inplace;
nkeysort_inplace { $_ } @inplace;
@copy = sort { $a <=> $b } @copy;
die 'nkeysort_inplace failed' unless "@inplace" eq "@copy";
print "Test 8 PASS: nkeysort_inplace modifies in place\n";

# Test 9: ukeysort (unsigned integer sort)
my @udata = map { int(rand(2**32)) } 1..1000;
die 'ukeysort failed' unless "@{[ukeysort { $_ } @udata]}" eq "@{[sort { $a <=> $b } @udata]}";
die 'rukeysort failed' unless "@{[rukeysort { $_ } @udata]}" eq "@{[sort { $b <=> $a } @udata]}";
print "Test 9 PASS: ukeysort and rukeysort (unsigned)\n";

# Test 10: Sort::Key::Natural
eval { require Sort::Key::Natural; };
if ($@) {
    print "Test 10 SKIP: Sort::Key::Natural not available\n";
} else {
    my @ndata = qw(foo1 foo23 foo foo2 foo6 bar12 bar1 bar2);
    my @nsorted = Sort::Key::Natural::natsort(@ndata);
    die 'natsort failed' unless "@nsorted" eq "bar1 bar2 bar12 foo foo1 foo2 foo6 foo23";
    print "Test 10 PASS: Sort::Key::Natural natsort works\n";
}

# Test 11: Sort::Key::Multi
eval { require Sort::Key::Multi; Sort::Key::Multi->import('ri_keysort'); };
if ($@) {
    print "Test 11 SKIP: Sort::Key::Multi not available\n";
} else {
    my @mdata = (1, 4, -5, -6, -2, 1000, 234);
    my @msorted = ri_keysort { $_ } @mdata;
    die 'ri_keysort failed' unless "@msorted" eq "@{[sort { $b <=> $a } @mdata]}";
    print "Test 11 PASS: Sort::Key::Multi ri_keysort works\n";
}

print "ALL TESTS PASSED\n";
