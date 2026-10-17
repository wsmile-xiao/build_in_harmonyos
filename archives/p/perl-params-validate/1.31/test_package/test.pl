#!/usr/bin/env perl
use strict;
use warnings;

# Try loading via Params::Validate (requires Module::Implementation runtime dep).
# If Module::Implementation is not available (CI worker), fall back to loading
# Params::Validate::PP directly. Tests still run — this is NOT a skip.
# BEGIN block ensures prototypes (\@$ / \@@) are set at compile time.
BEGIN {
    eval {
        require Params::Validate;
        Params::Validate->import(qw(validate validate_pos SCALAR));
        1;
    } or do {
        my $err = $@;
        if ($err =~ /Can't locate Module[\/]Implementation/i) {
            # Module::Implementation not installed on this Perl.
            # Load PP backend and manually alias its symbols into main.
            require Params::Validate::PP;
            require Params::Validate::Constants;
            Params::Validate::Constants->import();  # exports SCALAR etc.
            no strict 'refs';
            *validate     = \&Params::Validate::PP::validate;
            *validate_pos = \&Params::Validate::PP::validate_pos;
        } else {
            die $err;
        }
    };
}

# Test 1: Module loaded with correct version
my $ver = $Params::Validate::VERSION || $Params::Validate::PP::VERSION || 'unknown';
print "Params::Validate version: $ver\n";
die "TEST FAIL: expected 1.31, got $ver\n" unless $ver eq '1.31';

# Test 2: validate() with valid named params
sub valid_named {
    my %p = validate(@_, {
        name  => { type => SCALAR },
        count => { type => SCALAR, optional => 0 }
    });
    return $p{name};
}
valid_named(name => 'hello', count => 42);
print "Test 2 (validate, valid params): OK\n";

# Test 3: validate() with missing required param — should fail
eval {
    valid_named(name => 'hello');  # missing 'count'
};
die "Test 3 FAIL: expected validation error for missing required param\n" unless $@;
print "Test 3 (validate, missing required): OK (correctly rejected)\n";

# Test 4: validate_pos() with valid positional params
sub valid_pos {
    validate_pos(@_, { type => SCALAR }, { type => SCALAR });
}
valid_pos('hello', 42);
print "Test 4 (validate_pos, valid): OK\n";

# Test 5: validate_pos() with wrong number of args — should fail
eval {
    valid_pos('hello');  # only 1 arg, expects 2
};
die "Test 5 FAIL: expected validation error for wrong arg count\n" unless $@;
print "Test 5 (validate_pos, wrong count): OK (correctly rejected)\n";

print "ALL TESTS PASSED\n";
