#!/usr/bin/env python3
"""Conan test_package for cxxopts — verifies header present + real usage.

R34: include/cxxopts.hpp exists and a real compile+run using cxxopts works
(cxxopts::Options parse a flag + positional arg).
"""
import os
import subprocess
import sys
import tempfile

SMOKE_CPP = r'''
#include <cxxopts.hpp>
#include <cstdio>
int main(int argc, char** argv) {
    cxxopts::Options options("cxxopts smoke");
    int val = 0;
    options.add_options()
        ("v,verbose", "verbose flag")
        ("input", "input value", cxxopts::value<int>(val));
    auto result = options.parse(argc, argv);
    if (result.count("verbose")) { val = 1; }
    printf("cxxopts smoke: verbose=%d input=%d\n",
           result.count("verbose") ? 1 : 0, val);
    return 0;
}
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    if not os.path.isfile(os.path.join(inc, "cxxopts.hpp")):
        print(f"FAIL: cxxopts.hpp header missing: {inc}", file=sys.stderr)
        return 1
    tmpdir = tempfile.mkdtemp(prefix="cxxopts-smoke-")
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
        r = subprocess.run([binp, "-v", "42"], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL: run smoke: {r.stderr}", file=sys.stderr)
            return 1
        print(r.stdout.strip())
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
    print("OK: cxxopts header + real Options usage works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
