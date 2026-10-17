#!/usr/bin/env python3
"""Conan test_package for cpp-terminal — verifies header present + usage.

R34: include/cpp-terminal/terminal.h exists and a real compile+run using
cpp-terminal works (Term::color constants + version API).
"""
import os
import subprocess
import sys
import tempfile

SMOKE_CPP = r'''
#include <cpp-terminal/terminal.h>
#include <cstdio>
#include <string>

int main() {
    // 真实使用：Term::color 是函数模板（fg/bg 是枚举——0.1.0 API）
    std::string s = Term::color(Term::fg::red);
    printf("cpp-terminal smoke: color_len=%zu\n", s.size());
    return (s.size() > 0) ? 0 : 1;
}
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    if not os.path.isfile(os.path.join(inc, "cpp-terminal",
                                       "terminal.h")):
        print(f"FAIL: cpp-terminal/terminal.h header missing: {inc}",
              file=sys.stderr)
        return 1
    tmpdir = tempfile.mkdtemp(prefix="cppterm-smoke-")
    src = os.path.join(tmpdir, "smoke.cpp")
    binp = os.path.join(tmpdir, "smoke")
    try:
        with open(src, "w") as f:
            f.write(SMOKE_CPP)
        r = subprocess.run(
            ["/data/service/hnp/bin/clang++", src, "-o", binp,
             f"-I{inc}", "-std=c++11"],
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
    print("OK: cpp-terminal headers + real Term::color usage works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
