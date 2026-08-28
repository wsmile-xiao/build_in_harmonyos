#!/usr/bin/env python3
"""Conan test_package for tree-hh — verifies header present + real usage.

R34: include/tree.hh exists and a real compile+run using tree.hh works
(tree<int> insert + pre-order traversal).
"""
import os
import subprocess
import sys
import tempfile

SMOKE_CPP = r'''
#include <tree.hh>
#include <cstdio>

int main() {
    tree<int> t;
    tree<int>::iterator root = t.insert(t.begin(), 1);
    t.append_child(root, 2);
    t.append_child(root, 3);
    // 前序遍历计数
    int count = 0;
    for (tree<int>::iterator it = t.begin(); it != t.end(); ++it) {
        count++;
    }
    printf("tree.hh smoke: nodes=%d\n", count);
    return (count == 3) ? 0 : 1;
}
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    if not os.path.isfile(os.path.join(inc, "tree.hh")):
        print(f"FAIL: tree.hh header missing: {inc}", file=sys.stderr)
        return 1
    tmpdir = tempfile.mkdtemp(prefix="treehh-smoke-")
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
        r = subprocess.run([binp], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL: run smoke: {r.stderr}", file=sys.stderr)
            return 1
        print(r.stdout.strip())
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
    print("OK: tree.hh header + real tree<int> usage works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
