#!/usr/bin/env python3
"""missfits consumer test (L0c + R34): standalone test source executed
via self.run from conanfile.py test().

R34: actually invoke the tested CLI — missfits --help (real CLI call).

Usage: test_missfits.py <bindir>
"""
import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <bindir>", file=sys.stderr)
        return 2
    bindir = sys.argv[1]
    missfits = os.path.join(bindir, "missfits")
    if not os.path.isfile(missfits):
        raise AssertionError(f"missfits missing in {bindir}")
    # R34: missfits --help 输出用法（真实 CLI——无参数退出打印 SYNTAX）
    r = subprocess.run([missfits, "--help"], capture_output=True,
                       text=True, timeout=60)
    combined = (r.stdout + r.stderr).lower()
    if "syntax" not in combined:
        raise AssertionError(f"missfits --help failed: {r.stderr[:300]}")
    print("OK: missfits 2.8.0 (--help usage ok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
