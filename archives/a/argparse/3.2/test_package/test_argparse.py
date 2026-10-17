#!/usr/bin/env python3
"""Conan test_package for argparse — verifies header present + real usage.

R34: include/argparse/argparse.hpp exists and a real compile+run using
argparse works (ArgumentParser parse a flag + positional arg).
"""
import os
import subprocess
import sys
import tempfile

SMOKE_CPP = r'''
#include <argparse/argparse.hpp>
#include <cstdio>
int main(int argc, char** argv) {
    argparse::ArgumentParser program("argparse smoke");
    int input = 0;
    program.add_argument("--verbose", "-v").help("verbose flag").default_value(false);
    program.add_argument("input").scan<'i', int>();
    try {
        program.parse_args(argc, argv);
    } catch (const std::runtime_error& err) {
        printf("argparse smoke: parse error\n");
        return 1;
    }
    if (program.is_used("input")) {
        input = program.get<int>("input");
    }
    printf("argparse smoke: verbose=%d input=%d\n",
           program.get<bool>("--verbose") ? 1 : 0, input);
    return 0;
}
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    if not os.path.isfile(os.path.join(inc, "argparse", "argparse.hpp")):
        print(f"FAIL: argparse/argparse.hpp header missing: {inc}",
              file=sys.stderr)
        return 1
    tmpdir = tempfile.mkdtemp(prefix="argparse-smoke-")
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
    print("OK: argparse header + real ArgumentParser usage works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
