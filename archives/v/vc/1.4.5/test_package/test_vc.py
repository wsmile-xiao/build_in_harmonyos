#!/usr/bin/env python3
"""Conan test_package for vc — verifies headers present + real Vc usage.

R34: Vc/ headers exist and a real compile+run using Vc types works
(Vc::int_v vector addition, scalar fallback on OHOS aarch64).
"""
import os
import subprocess
import sys
import tempfile

SMOKE_CPP = r'''
#include <Vc/Vc>
#include <cstdio>
int main() {
    Vc::int_v a = Vc::int_v::Zero();
    Vc::int_v b = Vc::int_v::One();
    Vc::int_v c = a + b;
    // scalar fallback: all lanes == 1
    bool ok = true;
    for (int i = 0; i < Vc::int_v::Size; ++i) {
        if (c[i] != 1) { ok = false; break; }
    }
    printf("vc smoke: Size=%d ok=%s\n", Vc::int_v::Size, ok ? "true" : "false");
    return ok ? 0 : 1;
}
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    lib = os.path.join(pkg, "lib")
    if not os.path.isfile(os.path.join(inc, "Vc", "Vc")):
        print(f"FAIL: Vc/Vc header missing: {inc}", file=sys.stderr)
        return 1
    if not os.path.isfile(os.path.join(lib, "libVc.a")):
        print(f"FAIL: libVc.a missing: {lib}", file=sys.stderr)
        return 1
    tmpdir = tempfile.mkdtemp(prefix="vc-smoke-")
    src = os.path.join(tmpdir, "smoke.cpp")
    binp = os.path.join(tmpdir, "smoke")
    try:
        with open(src, "w") as f:
            f.write(SMOKE_CPP)
        r = subprocess.run(
            ["/data/service/hnp/bin/clang++", src, "-o", binp,
             f"-I{inc}", "-L{lib}".format(lib=lib), "-lVc", "-std=c++14"],
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
    print("OK: Vc headers + real Vc type usage works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
