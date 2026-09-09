#!/usr/bin/env python3
"""Test script for c2x 2.42 — verifies the structure conversion binary.

Tests (each runs the real packaged binary and asserts observable behaviour):
  1. Binary exists
  2. -h prints usage, exits 0
  3. no-args aborts gracefully with a message, exits non-zero
  4. -V reports "c2x version 2.42" and the no-SPGLIB configuration, exits 0
  5. CASTEP .cell -> XSF conversion produces a valid XSF file with the
     input lattice and both Si atoms

c2x prints its messages on stderr (verified upstream behaviour), so
assertions use the combined stdout+stderr stream.
"""
import subprocess
import sys
import os
import tempfile

SI_CELL = """%BLOCK LATTICE_CART
 5.43 0.0 0.0
 0.0 5.43 0.0
 0.0 0.0 5.43
%ENDBLOCK LATTICE_CART
%BLOCK POSITIONS_FRAC
 Si 0.0 0.0 0.0
 Si 0.25 0.25 0.25
%ENDBLOCK POSITIONS_FRAC
"""


def main():
    c2x = sys.argv[1]

    # Test 1: Binary exists
    if not os.path.isfile(c2x):
        print(f"FAIL: Binary not found at {c2x}", file=sys.stderr)
        sys.exit(1)
    print(f"PASS: Binary exists at {c2x}")

    def run(args, **kw):
        r = subprocess.run([c2x] + args, capture_output=True, text=True,
                           timeout=30, **kw)
        return r.returncode, r.stdout + r.stderr

    # Test 2: -h prints usage, exits 0
    rc, out = run(["-h"])
    if rc != 0:
        print(f"FAIL: -h exited with {rc}", file=sys.stderr)
        sys.exit(1)
    if "Usage: c2x" not in out:
        print(f"FAIL: Expected usage from -h, got: {out[:200]}", file=sys.stderr)
        sys.exit(1)
    print("PASS: -h prints usage")

    # Test 3: no-args fails gracefully
    rc, out = run([])
    if rc == 0:
        print("FAIL: no-args run should exit non-zero", file=sys.stderr)
        sys.exit(1)
    if "no input file" not in out:
        print(f"FAIL: Expected graceful 'no input file' message, got: {out[:200]}", file=sys.stderr)
        sys.exit(1)
    print("PASS: no-args aborts gracefully with a message")

    # Test 4: -V reports version and build configuration
    rc, out = run(["-V"])
    if rc != 0:
        print(f"FAIL: -V exited with {rc}", file=sys.stderr)
        sys.exit(1)
    if "c2x version 2.42" not in out:
        print(f"FAIL: Expected version banner from -V, got: {out[:200]}", file=sys.stderr)
        sys.exit(1)
    if "Not linked with spglib" not in out:
        print(f"FAIL: Expected no-SPGLIB build indicator from -V, got: {out[:200]}", file=sys.stderr)
        sys.exit(1)
    print("PASS: -V reports version 2.42 and no-SPGLIB configuration")

    # Test 5: real CASTEP .cell -> XSF conversion
    with tempfile.TemporaryDirectory() as td:
        cell = os.path.join(td, "si.cell")
        xsf = os.path.join(td, "si.xsf")
        with open(cell, "w") as handle:
            handle.write(SI_CELL)
        rc, out = run([cell, xsf])
        if rc != 0:
            print(f"FAIL: cell->xsf conversion exited with {rc}: {out[:200]}", file=sys.stderr)
            sys.exit(1)
        if not os.path.isfile(xsf):
            print("FAIL: conversion produced no output file", file=sys.stderr)
            sys.exit(1)
        with open(xsf) as handle:
            content = handle.read()
        for token in ("CRYSTAL", "PRIMVEC", "PRIMCOORD"):
            if token not in content:
                print(f"FAIL: XSF output missing {token}", file=sys.stderr)
                sys.exit(1)
        if "5.43" not in content:
            print("FAIL: XSF output missing input lattice constant 5.43", file=sys.stderr)
            sys.exit(1)
        # XSF writes atoms as atomic numbers (Si => 14), not element symbols
        if content.count("\n14 ") < 2:
            print("FAIL: XSF PRIMCOORD missing 2 silicon atoms (Z=14)", file=sys.stderr)
            sys.exit(1)
    print("PASS: CASTEP .cell -> XSF conversion is correct")

    print("\nAll 5 tests passed!")


if __name__ == "__main__":
    main()
