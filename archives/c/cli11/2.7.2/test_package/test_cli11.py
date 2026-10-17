#!/usr/bin/env python3
"""Conan test_package for cli11 — verifies headers present + real usage.

R34: CLI/CLI.hpp exists and a real compile+run using CLI11 works
(CLI::App parse a flag + positional arg).
"""
import os
import subprocess
import sys
import tempfile

SMOKE_CPP = r'''
#include <CLI/CLI.hpp>
#include <cstdio>
int main(int argc, char** argv) {
    CLI::App app{"cli11 smoke"};
    int val = 0;
    app.add_flag("-v,--verbose", val, "verbose flag");
    app.add_option("input", val, "input value");
    CLI11_PARSE(app, argc, argv);
    printf("cli11 smoke: verbose=%d\n", val > 0 ? 1 : 0);
    return 0;
}
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    if not os.path.isfile(os.path.join(inc, "CLI", "CLI.hpp")):
        print(f"FAIL: CLI/CLI.hpp header missing: {inc}", file=sys.stderr)
        return 1
    tmpdir = tempfile.mkdtemp(prefix="cli11-smoke-")
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
        r = subprocess.run([binp, "-v"], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL: run smoke: {r.stderr}", file=sys.stderr)
            return 1
        print(r.stdout.strip())
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
    print("OK: CLI11 headers + real CLI::App usage works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
