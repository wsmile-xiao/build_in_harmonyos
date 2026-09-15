#!/usr/bin/env python3
"""Consumer functional test for compartment 1.3.

Executes the installed compartment-user and compartment-root binaries with
real arguments and asserts real output content (not just exit code):

1. compartment-user --help exits 0 and prints Usage:
2. compartment-root --help exits 0 and prints Usage:
3. compartment-user --verify prints system capability output mentioning
   landlock, seccomp, or kernel (exit code is environment-dependent:
   0 when all checks pass, non-zero when Landlock is unavailable, so only
   the output content is asserted, never a fixed exit code).

Usage: python3 test_compartment.py <compartment-user> <compartment-root>
Prints a trailing "RESULT: N passed, M failed" line for the harness.
"""
import subprocess
import sys


def run(binary, *args):
    proc = subprocess.run(
        [binary] + list(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=20,
    )
    return proc.returncode, proc.stdout or ""


def main():
    user_bin, root_bin = sys.argv[1], sys.argv[2]
    passed = 0
    failed = 0

    rc, out = run(user_bin, "--help")
    if rc == 0 and out.strip() and "Usage:" in out:
        print("PASS: compartment-user --help prints usage")
        passed += 1
    else:
        print("FAIL: compartment-user --help (rc=%s, out=%r)" % (rc, out[:200]))
        failed += 1

    rc, out = run(root_bin, "--help")
    if rc == 0 and out.strip() and "Usage:" in out:
        print("PASS: compartment-root --help prints usage")
        passed += 1
    else:
        print("FAIL: compartment-root --help (rc=%s, out=%r)" % (rc, out[:200]))
        failed += 1

    rc, out = run(user_bin, "--verify")
    lowered = out.lower()
    if out.strip() and ("landlock" in lowered or "seccomp" in lowered or "kernel" in lowered):
        print("PASS: compartment-user --verify reports capabilities (rc=%s)" % rc)
        passed += 1
    else:
        print("FAIL: compartment-user --verify produced no capability output (rc=%s, out=%r)" % (rc, out[:200]))
        failed += 1

    print("RESULT: %d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
