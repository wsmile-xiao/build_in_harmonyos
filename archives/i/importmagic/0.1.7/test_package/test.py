#!/usr/bin/env python3
"""Test importmagic can be imported and reports the correct version."""
import sys
import importmagic

expected = "0.1.7"
actual = importmagic.__version__

if actual != expected:
    print(f"FAIL: __version__ expected {expected!r}, got {actual!r}")
    sys.exit(1)

print(f"importmagic {actual} — OK")
sys.exit(0)
