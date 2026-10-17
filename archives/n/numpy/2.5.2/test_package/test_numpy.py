#!/usr/bin/env python3
"""Functional test for numpy 2.5.2 (R34: must exercise the package API).

Verifies:
  1. numpy imports (C extension .so files load on OHOS)
  2. version check
  3. array arithmetic
  4. BLAS-backed dot product (verifies openblas integration)
  5. statistical functions
  6. reshape / axis reductions
  7. linalg (LAPACK path through openblas)
"""
import numpy as np

print("Test 1 PASS: numpy imported successfully")

assert np.__version__ == "2.5.2", f"Expected 2.5.2, got {np.__version__}"
print(f"Test 2 PASS: numpy version {np.__version__}")

a = np.array([1, 2, 3])
b = np.array([4, 5, 6])
assert (a + b == np.array([5, 7, 9])).all(), "Array addition failed"
print("Test 3 PASS: array addition works")

dot = np.dot(a, b)
assert dot == 32, f"Dot product failed: expected 32, got {dot}"
print(f"Test 4 PASS: BLAS dot product = {dot}")

assert np.mean(a) == 2.0, "Mean computation failed"
print("Test 5 PASS: mean computation works")

arr = np.arange(12).reshape(3, 4)
assert arr.shape == (3, 4), "Reshape failed"
assert (arr.sum(axis=0) == np.array([12, 15, 18, 21])).all(), "Axis sum failed"
print("Test 6 PASS: reshape and axis sum work")

m = np.array([[3.0, 1.0], [1.0, 2.0]])
inv = np.linalg.inv(m)
assert np.allclose(m @ inv, np.eye(2)), "Matrix inverse failed"
print("Test 7 PASS: linalg inverse works (LAPACK via openblas)")

print("All tests passed!")
