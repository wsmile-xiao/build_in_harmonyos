#!/usr/bin/env python3
"""Conan test_package for frozen — verifies header present + real usage.

R34: include/frozen/map.h exists and a real compile+run using frozen works
(frozen::map constexpr construction + lookup).
"""
import os
import subprocess
import sys
import tempfile

SMOKE_CPP = r'''
#include <frozen/map.h>
#include <cstdio>

// constexpr frozen::map（编译期构造）
constexpr frozen::map<int, int, 2> m = {{1, 10}, {2, 20}};

int main() {
    auto it = m.find(2);
    int v = (it != m.end()) ? it->second : -1;
    printf("frozen smoke: m[2]=%d\n", v);
    return (v == 20) ? 0 : 1;
}
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    if not os.path.isfile(os.path.join(inc, "frozen", "map.h")):
        print(f"FAIL: frozen/map.h header missing: {inc}", file=sys.stderr)
        return 1
    tmpdir = tempfile.mkdtemp(prefix="frozen-smoke-")
    src = os.path.join(tmpdir, "smoke.cpp")
    binp = os.path.join(tmpdir, "smoke")
    try:
        with open(src, "w") as f:
            f.write(SMOKE_CPP)
        r = subprocess.run(
            ["/data/service/hnp/bin/clang++", src, "-o", binp,
             f"-I{inc}", "-std=c++14"],
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
    print("OK: frozen headers + real frozen::map usage works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
