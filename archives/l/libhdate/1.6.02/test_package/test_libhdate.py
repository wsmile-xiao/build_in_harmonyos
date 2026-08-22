#!/usr/bin/env python3
"""libhdate consumer test (L0c + R34: standalone test source executed
via self.run from conanfile.py test()).

hcal/hdate are Hebrew calendar CLI tools — date calculations run fine
on OHOS (no env restrictions): actually execute hdate and verify its
output (real execution, R34). Also verify the library + headers.

Usage: test_libhdate.py <package-folder>
"""
import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <package-folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    # 真实执行 hdate（希伯来历法日期——今天输出，R34 真实运行）
    exe = os.path.join(pkg, "bin", "hdate")
    if not os.path.isfile(exe):
        raise AssertionError(f"hdate binary missing: {exe}")
    if not os.access(exe, os.X_OK):
        raise AssertionError(f"hdate not executable: {exe}")
    r = subprocess.run([exe], capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        raise AssertionError(f"hdate failed rc={r.returncode}: {r.stderr[:120]}")
    if not r.stdout.strip():
        raise AssertionError("hdate produced no output")
    # 库存在 + ELF
    libdir = os.path.join(pkg, "lib")
    found = [f for f in os.listdir(libdir)
             if f.startswith("libhdate") and (f.endswith(".a") or
                                              f.endswith(".so"))]
    if not found:
        raise AssertionError(f"libhdate missing in {libdir}")
    lib = os.path.join(libdir, found[0])
    with open(lib, "rb") as f:
        magic = f.read(4)
    if magic != b"\x7fELF":
        raise AssertionError(f"{lib} is not an ELF library")
    inc = os.path.join(pkg, "include", "libhdate.h")
    if not os.path.isfile(inc):
        raise AssertionError(f"libhdate.h missing: {inc}")
    print(f"OK: hdate executed — {r.stdout.strip().splitlines()[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
