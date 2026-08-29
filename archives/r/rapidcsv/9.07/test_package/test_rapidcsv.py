#!/usr/bin/env python3
"""Conan test_package for rapidcsv — verifies header present + real usage.

R34: include/rapidcsv.h exists and a real compile+run using rapidcsv works
(Document parse CSV from an in-memory string).
"""
import os
import subprocess
import sys
import tempfile

SMOKE_CPP = r'''
#include <rapidcsv.h>
#include <cstdio>
#include <string>
int main() {
    // in-memory CSV: col0, col1
    //               1,    2
    //               3,    4
    std::istringstream csv("col0,col1\n1,2\n3,4\n");
    rapidcsv::Document doc(csv, rapidcsv::LabelParams(0, 0));
    int v = doc.GetCell<int>("col1", 1);
    printf("rapidcsv smoke: col1 row1 = %d\n", v);
    return (v == 4) ? 0 : 1;
}
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    if not os.path.isfile(os.path.join(inc, "rapidcsv.h")):
        print(f"FAIL: rapidcsv.h header missing: {inc}", file=sys.stderr)
        return 1
    tmpdir = tempfile.mkdtemp(prefix="rapidcsv-smoke-")
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
    print("OK: rapidcsv header + real Document usage works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
