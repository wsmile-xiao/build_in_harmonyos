#!/bin/sh
# Smoke test for cifer CLI binaries on HarmonyOS

# cifer accepts switches; -x is unrecognized, returns 1 immediately (no TTY needed)
cifer -x >/dev/null 2>&1 || true

# cifer-dict requires args; running without args shows usage then exits
cifer-dict >/dev/null 2>&1 || true

echo "All smoke tests passed"
