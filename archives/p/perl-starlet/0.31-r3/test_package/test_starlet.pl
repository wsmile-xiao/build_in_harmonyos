#!/usr/bin/env perl
# test_package/test_starlet.pl — Functional test for Starlet Perl module
# Run via: perl -I<lib_dir> test_starlet.pl
use strict;
use warnings;

my $pass = 0;
my $fail = 0;
my $skip = 0;

# Test 1+2: Module loads and version check (combined to avoid die on missing namespace)
eval {
    require Starlet;
    my $version = Starlet->VERSION;
    if (defined $version && $version eq '0.31') {
        $pass += 2;
    } else {
        die "Version mismatch: got '" . ($version // 'undef') . "', expected '0.31'\n";
    }
};
if ($@) {
    print "FAIL: $@\n";
    $fail += 2;
}

# Test 3: Starlet::Server loads (core server module)
# Starlet::Server is part of the Starlet package but requires Plack, Parallel::Prefork etc.
# Missing runtime dependency → SKIP; any other error → FAIL (real regression).
eval { require Starlet::Server };
if ($@) {
    if ($@ =~ m{Can't locate [\w/:]+\.pm in \@INC}) {
        print "SKIP: Starlet::Server not loadable (runtime dependencies not installed)\n";
        $skip++;
    } else {
        print "FAIL: Starlet::Server load error: $@\n";
        $fail++;
    }
} else {
    $pass++;
}

# Test 4: Plack::Handler::Starlet loads (core handler module)
eval { require Plack::Handler::Starlet };
if ($@) {
    if ($@ =~ m{Can't locate [\w/:]+\.pm in \@INC}) {
        print "SKIP: Plack::Handler::Starlet not loadable (runtime dependencies not installed)\n";
        $skip++;
    } else {
        print "FAIL: Plack::Handler::Starlet load error: $@\n";
        $fail++;
    }
} else {
    $pass++;
}

if ($fail == 0) {
    print "PASS: $pass tests passed, $skip skipped\n";
} else {
    print "FAIL: $fail tests failed\n";
}
exit($fail > 0 ? 1 : 0);
