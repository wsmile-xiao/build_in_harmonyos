#!/bin/sh
set -eu

DEMUMBLE=${1:-demumble}

# HarmonyOS PC exposes HMDFS mounts; checking one prevents this test from being
# silently counted as a generic desktop-Linux run.
mount | grep -q ' type hmdfs ' || {
    echo "FAIL: HarmonyOS HMDFS mount not detected" >&2
    exit 1
}

actual=$("$DEMUMBLE" _ZN2zx7channelD4Ev)
[ "$actual" = 'zx::channel::~channel()' ] || {
    echo "FAIL: HarmonyOS runtime demangling returned: $actual" >&2
    exit 1
}

echo "HarmonyOS-specific HMDFS runtime test passed"
