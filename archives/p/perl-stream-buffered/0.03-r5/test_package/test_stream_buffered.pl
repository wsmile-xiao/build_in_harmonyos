#!/usr/bin/env perl
# test_package/test_stream_buffered.pl — Functional test for Stream::Buffered
# Run via: perl -I<lib_dir> test_stream_buffered.pl
use strict;
use warnings;
use Stream::Buffered;

my $pass = 0;
my $fail = 0;

# Test 1: Module loads and can create buffer
eval {
    my $buf = Stream::Buffered->new();
    $pass++;
};
if ($@) {
    print "FAIL: Cannot create Stream::Buffered: $@\n";
    $fail++;
}

# Test 2: print and size
eval {
    my $buf = Stream::Buffered->new();
    $buf->print("hello");
    my $size = $buf->size;
    if (defined $size && $size == 5) {
        $pass++;
    } else {
        print "FAIL: Expected size 5, got '" . ($size // 'undef') . "'\n";
        $fail++;
    }
};
if ($@) {
    print "FAIL: print/size test: $@\n";
    $fail++;
}

# Test 3: rewind and read
eval {
    my $buf = Stream::Buffered->new();
    $buf->print("test data");
    my $fh = $buf->rewind;
    my $line = do { local $/; <$fh> };
    if (defined $line && $line eq "test data") {
        $pass++;
    } else {
        print "FAIL: Expected 'test data', got '" . ($line // 'undef') . "'\n";
        $fail++;
    }
};
if ($@) {
    print "FAIL: rewind/read test: $@\n";
    $fail++;
}

if ($fail == 0) {
    print "PASS: All $pass tests passed\n";
} else {
    print "FAIL: $fail tests failed\n";
}
exit($fail > 0 ? 1 : 0);
