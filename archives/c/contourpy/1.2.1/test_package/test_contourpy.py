#!/usr/bin/env python3
"""Functional test for contourpy 1.2.1 (R34: must exercise the package API).

Verifies:
  1. contourpy imports (C extension .so loads on OHOS)
  2. version check
  3. contour generation from a filled contour computation (core API)
  4. contour lines from grid data via numpy integration
"""
import numpy as np
import contourpy as cpy

print("Test 1 PASS: contourpy imported successfully")

assert cpy.__version__ == "1.2.1", f"Expected 1.2.1, got {cpy.__version__}"
print(f"Test 2 PASS: contourpy version {cpy.__version__}")

# Core API: filled contours on a simple grid
x, y = np.meshgrid(np.linspace(0.0, 1.0, 5), np.linspace(0.0, 1.0, 5))
z = x + y
cont_gen = cpy.contour_generator(x, y, z, name="serial")
filled = cont_gen.filled(0.5, 1.0)
assert filled is not None and len(filled) >= 1, "filled contours missing"
assert filled[0] is not None, "lower contour geometry missing"
print("Test 3 PASS: filled contour generation works (serial backend)")

# Contour lines
lines = cont_gen.lines(0.75)
assert lines is not None, "contour lines missing"
print("Test 4 PASS: contour line generation works")

print("All tests passed!")
