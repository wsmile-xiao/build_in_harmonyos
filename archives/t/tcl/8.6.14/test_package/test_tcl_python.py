#!/usr/bin/env python3
"""test_tcl_python.py — Python consumer test for tcl 8.6.14.

Consumes the packaged tclsh8.6 binary directly from Python (the exact
consumer pattern of a Python-based build tooling that shells out to Tcl),
driving the interpreter through stdin via subprocess.run().

Usage: test_tcl_python.py <absolute-path-to-tclsh8.6>

Assertions:
  A1: tclsh path exists and is executable
  A2: subprocess return code is 0
  A3: `puts [info patchlevel]` outputs 8.6.14
  A4: `puts [expr {6 * 7}]` outputs 42
"""
import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"[FAIL] usage: {sys.argv[0]} <absolute-path-to-tclsh8.6>")
        return 1
    tclsh = sys.argv[1]

    # A1: tclsh path exists and is executable
    if not os.path.isfile(tclsh) or not os.access(tclsh, os.X_OK):
        print(f"[FAIL] tclsh not found or not executable: {tclsh}")
        return 1
    print(f"[PASS] tclsh exists and is executable: {tclsh}")

    # Drive the packaged tclsh8.6 through stdin via subprocess.run()
    script = "puts [info patchlevel]\nputs [expr {6 * 7}]\n"
    proc = subprocess.run(
        [tclsh],
        input=script,
        capture_output=True,
        text=True,
    )

    # A2: subprocess return code is 0
    if proc.returncode != 0:
        print(f"[FAIL] tclsh returned rc={proc.returncode}, stderr: {proc.stderr.strip()}")
        return 1
    print(f"[PASS] tclsh exited with rc=0")

    out_lines = [ln.strip() for ln in proc.stdout.splitlines()]

    # A3: `puts [info patchlevel]` outputs 8.6.14
    if out_lines and out_lines[0] == "8.6.14":
        print(f"[PASS] patchlevel: {out_lines[0]}")
    else:
        got = out_lines[0] if out_lines else "<empty>"
        print(f"[FAIL] unexpected patchlevel: '{got}' (expected 8.6.14)")
        return 1

    # A4: `puts [expr {6 * 7}]` outputs 42
    if len(out_lines) >= 2 and out_lines[1] == "42":
        print(f"[PASS] expr {{6 * 7}} = {out_lines[1]}")
    else:
        got = out_lines[1] if len(out_lines) >= 2 else "<missing>"
        print(f"[FAIL] unexpected expr result: '{got}' (expected 42)")
        return 1

    print("=== Python consumer test passed (4 assertions) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
