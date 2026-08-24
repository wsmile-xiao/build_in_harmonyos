#!/usr/bin/env python3
"""psfex consumer test (L0c + R34): standalone test source executed via
self.run from conanfile.py test().

R34: actually invoke the tested CLI — psfex --help (no upstream test
data in sdist; make check requires SExtractor catalogs not shipped).

Usage: test_psfex.py <bindir>
"""
import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <bindir>", file=sys.stderr)
        return 2
    bindir = sys.argv[1]
    psfex = os.path.join(bindir, "psfex")
    if not os.path.isfile(psfex):
        raise AssertionError(f"psfex missing in {bindir}")
    # R34: psfex --help 输出用法（真实 CLI——无参数退出会打印 SYNTAX）
    r = subprocess.run([psfex, "--help"], capture_output=True, text=True,
                       timeout=60)
    combined = (r.stdout + r.stderr).lower()
    if "syntax" not in combined:
        raise AssertionError(f"psfex --help failed: {r.stderr[:300]}")
    print("OK: psfex 3.24.2 (--help usage ok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
