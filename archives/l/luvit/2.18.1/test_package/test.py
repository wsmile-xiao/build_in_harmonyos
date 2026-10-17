#!/usr/bin/env python3
"""test_package/test.py — luvit 2.18.1 smoke test.

Verifies the luvit runtime is functional: version output and Lua execution.
The luvit launcher path is passed via LUVIT_BIN env (set by conanfile.py).
"""
import os
import subprocess
import sys


def main():
    luvit = os.environ.get("LUVIT_BIN", "")
    if not luvit or not os.path.exists(luvit):
        print("FAIL: LUVIT_BIN not set or missing:", luvit)
        return 1

    # Test 1: --version
    r = subprocess.run([luvit, "--version"], capture_output=True, text=True, timeout=30)
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        print("FAIL: luvit --version rc=%d" % r.returncode)
        print(out)
        return 1
    if "luvit version:" not in out and "Luvit" not in out and "2.18.1" not in out:
        print("FAIL: --version output unexpected:", out)
        return 1
    print("✅ luvit --version OK")
    print(out.strip().splitlines()[0] if out.strip() else "")

    # Test 2: execute Lua code via -e
    r = subprocess.run([luvit, "-e", 'print("luvit smoke OK")'],
                       capture_output=True, text=True, timeout=30)
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0 or "luvit smoke OK" not in out:
        print("FAIL: luvit -e rc=%d out=%r" % (r.returncode, out))
        return 1
    print("✅ luvit -e 'print(...)' OK")

    print("\n✅ All luvit tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
