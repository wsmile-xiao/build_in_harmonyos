#!/usr/bin/env python3
"""Conan test_package for dynamic-bitset — verifies header present + usage.

R34: include/sul/dynamic_bitset.hpp exists and a real compile+run using
dynamic_bitset works (sul::dynamic_bitset set/test + count).
"""
import os
import subprocess
import sys
import tempfile

SMOKE_CPP = r'''
#include <sul/dynamic_bitset.hpp>
#include <cstdio>

int main() {
    sul::dynamic_bitset<> b(8);
    b.set(1);
    b.set(3);
    printf("dynamic_bitset smoke: count=%zu test2=%d\n",
           b.count(), b.test(2) ? 1 : 0);
    return (b.count() == 2 && !b.test(2)) ? 0 : 1;
}
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    if not os.path.isfile(os.path.join(inc, "sul", "dynamic_bitset.hpp")):
        print(f"FAIL: sul/dynamic_bitset.hpp header missing: {inc}",
              file=sys.stderr)
        return 1
    tmpdir = tempfile.mkdtemp(prefix="dynbitset-smoke-")
    src = os.path.join(tmpdir, "smoke.cpp")
    binp = os.path.join(tmpdir, "smoke")
    try:
        with open(src, "w") as f:
            f.write(SMOKE_CPP)
        r = subprocess.run(
            ["/data/service/hnp/bin/clang++", src, "-o", binp,
             f"-I{inc}", "-std=c++17"],
            capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL: compile smoke: {r.stderr}", file=sys.stderr)
            return 1
        r = subprocess.run([binp], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL: run smoke: {r.stderr}", file=sys.stderr)
            return 1
        print(r.stdout.strip())
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
    print("OK: dynamic_bitset header + real sul::dynamic_bitset usage works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
