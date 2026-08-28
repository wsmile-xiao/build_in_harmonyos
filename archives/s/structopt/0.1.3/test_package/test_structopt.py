#!/usr/bin/env python3
"""Conan test_package for structopt — verifies header present + usage.

R34: include/structopt/app.hpp exists and a real compile+run using
structopt works (structopt::app parse a struct field).
"""
import os
import subprocess
import sys
import tempfile

SMOKE_CPP = r'''
#include <structopt/app.hpp>
#include <cstdio>

struct Options {
    int value = 0;
};
STRUCTOPT(Options, value);

int main(int argc, char** argv) {
    try {
        auto options = structopt::app("structopt smoke").parse<Options>(argc, argv);
        printf("structopt smoke: value=%d\n", options.value);
        return 0;
    } catch (structopt::exception& e) {
        printf("structopt smoke: parse error\n");
        return 1;
    }
}
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    if not os.path.isfile(os.path.join(inc, "structopt", "app.hpp")):
        print(f"FAIL: structopt/app.hpp header missing: {inc}",
              file=sys.stderr)
        return 1
    tmpdir = tempfile.mkdtemp(prefix="structopt-smoke-")
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
        r = subprocess.run([binp, "42"], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL: run smoke: {r.stderr}", file=sys.stderr)
            return 1
        print(r.stdout.strip())
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
    print("OK: structopt header + real structopt::app usage works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
