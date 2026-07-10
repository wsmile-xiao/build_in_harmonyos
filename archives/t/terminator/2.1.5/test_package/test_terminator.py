#!/usr/bin/env python3
"""Smoke test for terminator 2.1.5 — verifies terminatorlib imports and version matches."""
import sys

import terminatorlib
from terminatorlib.version import APP_NAME, APP_VERSION

if APP_NAME != "terminator":
    print(f"FAIL: Expected terminator, got {APP_NAME}", file=sys.stderr)
    sys.exit(1)
if APP_VERSION != "2.1.5":
    print(f"FAIL: Expected 2.1.5, got {APP_VERSION}", file=sys.stderr)
    sys.exit(1)

print(f"{APP_NAME} {APP_VERSION} import OK")
print(f"Module path: {terminatorlib.__file__}")
sys.exit(0)
