#!/bin/sh
# Independent test source for recc (L0c requirement).
# Verifies the recc binary runs on HarmonyOS PC and reports its version.
set -e
if ! recc --version 2>&1; then
    echo "FAIL: recc --version did not exit cleanly" >&2
    exit 1
fi
# recc with no args must not crash (exits non-zero is fine).
recc >/dev/null 2>&1 || true
echo "PASS: recc smoke test"
