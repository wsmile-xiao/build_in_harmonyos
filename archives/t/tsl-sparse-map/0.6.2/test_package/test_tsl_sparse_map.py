#!/usr/bin/env python3
"""tsl-sparse-map consumer test (R34): header exists + real tsl::sparse_map
usage (compile+run smoke — insert/find/erase via the packaged headers)."""
import os
import subprocess
import sys
import tempfile

SMOKE_CPP = r'''
#include <tsl/sparse_map.h>
#include <string>
#include <iostream>

int main() {
    // 真实 API 使用：sparse_map insert/find/erase
    tsl::sparse_map<int, std::string> map;
    map.insert({1, "one"});
    map.insert({2, "two"});
    if (map.size() != 2) { std::cout << "FAIL: size\n"; return 1; }
    auto it = map.find(1);
    if (it == map.end() || it.value() != "one") {
        std::cout << "FAIL: find(1)\n"; return 1;
    }
    map.erase(2);
    if (map.count(2) != 0) { std::cout << "FAIL: erase(2)\n"; return 1; }
    std::cout << "OK: sparse_map insert/find/erase works\n";
    return 0;
}
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    hdr = os.path.join(inc, "tsl", "sparse_map.h")
    if not os.path.isfile(hdr):
        print(f"FAIL: sparse_map.h missing: {hdr}", file=sys.stderr)
        return 1
    tmpdir = tempfile.mkdtemp(prefix="tsl-sparse-map-")
    src = os.path.join(tmpdir, "smoke.cpp")
    binp = os.path.join(tmpdir, "smoke")
    try:
        with open(src, "w") as f:
            f.write(SMOKE_CPP)
        cxx = "/data/service/hnp/bin/clang++"
        if not os.path.isfile(cxx):
            cxx = "clang++"
        r = subprocess.run([cxx, src, "-o", binp, f"-I{inc}",
                            "-std=c++17"],
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
    print("OK: tsl-sparse-map header + tsl::sparse_map real API works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
