#!/bin/bash
# test_object_event.sh — Object::Event consumer test
# Verifies that Object::Event can be loaded and its API works correctly
set -euo pipefail

# PERL5LIB is set by Conan's conanrun environment, which includes:
#   Package's lib/perl5 path (Object::Event itself)
# No additional system paths needed — patch removes common::sense/AnyEvent deps.

# Test 1: Module loads successfully
perl -MObject::Event -e 'exit 0'
echo "[PASS] Object::Event module loads"

# Test 2: Version is accessible
VERSION=$(perl -MObject::Event -e 'print Object::Event->VERSION')
if [ -n "$VERSION" ]; then
    echo "[PASS] Object::Event version: $VERSION"
else
    echo "[FAIL] Could not get Object::Event version"
    exit 1
fi

# Test 3: Basic event API — register and fire callback
perl -MObject::Event -e '
    my $obj = Object::Event->new;
    my $fired = 0;
    my $guard = $obj->reg_cb(test_event => sub { $fired = 1; });
    $obj->event(test_event => ());
    die "Event callback not fired" unless $fired;
    print "[PASS] Event register and fire works\n";
' 2>&1

# Test 4: unregister callback
perl -MObject::Event -e '
    my $obj = Object::Event->new;
    my $count = 0;
    my $cb = $obj->reg_cb(test_event => sub { $count++; });
    $obj->event(test_event => ());
    $obj->unreg_cb($cb);
    $obj->event(test_event => ());
    die "unreg_cb did not stop callback" if $count != 1;
    print "[PASS] unreg_cb works correctly\n";
' 2>&1

# Test 5: Guard auto-unregister (scope-guard DESTROY triggers unreg_cb)
perl -MObject::Event -e '
    my $obj = Object::Event->new;
    my $count = 0;
    {
        my $guard = $obj->reg_cb(test_event => sub { $count++; });
        $obj->event(test_event => ());
        die "Guard: callback did not fire" if $count != 1;
        # $guard goes out of scope here — DESTROY calls unreg_cb
    }
    $obj->event(test_event => ());
    die "Guard auto-unregister failed: callback fired after scope exit" if $count != 1;
    print "[PASS] Guard auto-unregister works correctly\n";
' 2>&1

echo "All tests passed."
