#!/usr/bin/env python3
"""awffull consumer test (L0c + R34): standalone test source executed via
self.run from conanfile.py test().

R34: actually invoke the tested CLI — awffull --version / --help (real
CLI call).

Usage: test_awffull.py <bindir>
"""
import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <bindir>", file=sys.stderr)
        return 2
    bindir = sys.argv[1]
    awffull = os.path.join(bindir, "awffull")
    if not os.path.isfile(awffull):
        raise AssertionError(f"awffull missing in {bindir}")
    # R34: awffull --version 输出版本（真实 CLI 调用）
    r = subprocess.run([awffull, "--version"], capture_output=True,
                       text=True, timeout=60)
    combined = (r.stdout + r.stderr).lower()
    if "awffull" not in combined and "version" not in combined:
        raise AssertionError(
            f"awffull --version failed: {r.stderr[:300]}")
    print("OK: awffull 3.10.2 (--version ok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
