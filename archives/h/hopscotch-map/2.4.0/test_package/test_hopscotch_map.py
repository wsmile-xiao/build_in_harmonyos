#!/usr/bin/env python3
"""hopscotch-map consumer test (R34): header exists + real tsl::hopscotch_map
usage (compile+run smoke — insert/find/erase via the packaged headers)."""
import os
import subprocess
import sys
import tempfile

SMOKE_CPP = r'''
#include <tsl/hopscotch_map.h>
#include <iostream>

int main() {
    // 真实 API 使用：hopscotch_map insert/find/erase
    tsl::hopscotch_map<int, std::string> map;
    map.insert({1, "one"});
    map.insert({2, "two"});
    if (map.size() != 2) { std::cout << "FAIL: size\n"; return 1; }
    auto it = map.find(1);
    if (it == map.end() || it.value() != "one") {
        std::cout << "FAIL: find(1)\n"; return 1;
    }
    map.erase(2);
    if (map.count(2) != 0) { std::cout << "FAIL: erase(2)\n"; return 1; }
    std::cout << "OK: hopscotch_map insert/find/erase works\n";
    return 0;
}
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    hdr = os.path.join(inc, "tsl", "hopscotch_map.h")
    if not os.path.isfile(hdr):
        print(f"FAIL: hopscotch_map.h missing: {hdr}", file=sys.stderr)
        return 1
    tmpdir = tempfile.mkdtemp(prefix="hopscotch-map-")
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
    print("OK: hopscotch-map header + tsl::hopscotch_map real API works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
