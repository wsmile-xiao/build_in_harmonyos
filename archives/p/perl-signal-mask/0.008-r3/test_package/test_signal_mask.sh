#!/bin/sh
# test_package/test_signal_mask.sh — smoke test for perl-signal-mask 0.008-r3
# Called by test_package/conanfile.py via self.run()
# PERL5LIB must be set by the caller (Conan runenv_info from package_info)
set -eu

# Test 1: Load Signal::Mask
echo "[test] 1/5: Load Signal::Mask"
if perl -MSignal::Mask -e 'print "OK\n"' 2>/dev/null; then
    echo "PASS: Signal::Mask loaded"
else
    echo "FAIL: Signal::Mask load test failed"
    exit 1
fi

# Test 2: Load Signal::Pending
echo "[test] 2/5: Load Signal::Pending"
if perl -MSignal::Pending -e 'print "OK\n"' 2>/dev/null; then
    echo "PASS: Signal::Pending loaded"
else
    echo "FAIL: Signal::Pending load test failed"
    exit 1
fi

# Test 3: Verify version
echo "[test] 3/5: Verify version"
if perl -MSignal::Mask -e 'die unless $Signal::Mask::VERSION eq "0.008"; print "Version OK\n"' 2>/dev/null; then
    echo "PASS: Version 0.008 verified"
else
    echo "FAIL: Version check failed"
    exit 1
fi

# Test 4: Functional test — set signal mask via tied hash
echo "[test] 4/5: Functional signal mask test"
if perl -e 'use strict; use warnings; use Signal::Mask; $Signal::Mask{USR1} = 1; print "Signal mask set OK\n"' 2>/dev/null; then
    echo "PASS: Signal mask set/clear works"
else
    echo "FAIL: Functional test failed"
    exit 1
fi

# Test 5: Signal::Pending tied hash API — read pending status
echo "[test] 5/5: Signal::Pending tied hash API"
if perl -e 'use strict; use warnings; use Signal::Pending; my $pending = $Signal::Pending{USR1}; print "Pending check OK: USR1=$pending\n"' 2>/dev/null; then
    echo "PASS: Signal::Pending tied hash API works"
else
    echo "FAIL: Signal::Pending API test failed"
    exit 1
fi

echo "All 5/5 tests passed."
