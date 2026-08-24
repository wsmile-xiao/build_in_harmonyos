#!/usr/bin/env python3
"""skymaker consumer test (L0c + R34): standalone test source executed
via self.run from conanfile.py test().

R34: actually invoke the tested CLI — sky --help (real CLI call).

Usage: test_skymaker.py <bindir>
"""
import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <bindir>", file=sys.stderr)
        return 2
    bindir = sys.argv[1]
    sky = os.path.join(bindir, "sky")
    if not os.path.isfile(sky):
        raise AssertionError(f"sky missing in {bindir}")
    # R34: sky --help 输出用法（真实 CLI——无参数退出打印 SYNTAX）
    r = subprocess.run([sky, "--help"], capture_output=True, text=True,
                       timeout=60)
    combined = (r.stdout + r.stderr).lower()
    if "syntax" not in combined:
        raise AssertionError(f"sky --help failed: {r.stderr[:300]}")
    print("OK: skymaker 3.10.5 (--help usage ok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
