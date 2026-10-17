#!/usr/bin/env python3
"""Conan test_package for inipp — verifies header present + real usage.

R34: include/inipp/inipp.h exists and a real compile+run using inipp works
(inipp::Ini parse an in-memory INI string, extract a value).
"""
import os
import subprocess
import sys
import tempfile

SMOKE_CPP = r'''
#include <inipp/inipp.h>
#include <cstdio>
#include <sstream>
#include <string>

int main() {
    // in-memory INI: [section] key=value
    std::istringstream in("[section]\nkey=42\n");
    inipp::Ini<char> ini;
    ini.parse(in);
    int val = 0;
    // get_value(sec, key, dst) —— 3 参数签名（sec 是整节 map）
    inipp::get_value(ini.sections["section"], "key", val);
    printf("inipp smoke: key=%d\n", val);
    return (val == 42) ? 0 : 1;
}
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    if not os.path.isfile(os.path.join(inc, "inipp", "inipp.h")):
        print(f"FAIL: inipp/inipp.h header missing: {inc}", file=sys.stderr)
        return 1
    tmpdir = tempfile.mkdtemp(prefix="inipp-smoke-")
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
    print("OK: inipp header + real Ini usage works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
