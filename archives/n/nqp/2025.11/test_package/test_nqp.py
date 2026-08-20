#!/usr/bin/env python3
"""Run the packaged NQP executable and assert real language behavior."""

import subprocess
import sys


nqp, script = sys.argv[1:]
version = subprocess.run([nqp, "--version"], check=True, text=True, capture_output=True)
if "2025.11" not in version.stdout:
    raise AssertionError(f"unexpected NQP version: {version.stdout!r}")

result = subprocess.run([nqp, script], check=True, text=True, capture_output=True)
actual = result.stdout.splitlines()
expected = [
    "arithmetic=42",
    "string=mqtt-nqp",
    "array-elems=3",
    "array-value=8",
    "hash-value=mqtt",
    "hash-exists=1",
    "class-value=7",
    "nqp-smoke=ok",
]
if len(actual) != len(expected):
    raise AssertionError(f"unexpected NQP output count: {actual!r}")
for index, (observed, wanted) in enumerate(zip(actual, expected), start=1):
    if observed != wanted:
        raise AssertionError(
            f"NQP output check {index} failed: expected {wanted!r}, got {observed!r}"
        )
print("NQP consumer behavior checks passed: version + count + 8 output checks")
