#!/usr/bin/env python3
"""Conan test_package for fast-cpp-csv-parser — verifies header + real usage.

R34: include/csv.h exists and a real compile+run using CSVReader parses
an in-memory CSV into a struct (with -lpthread per upstream README).
"""
import os
import shutil
import subprocess
import sys
import tempfile

SMOKE_CPP = r'''
#include "csv.h"
#include <cstdio>
#include <string>

struct Row {
    std::string name;
    int value;
};

int main(int argc, char** argv) {
    // CSVReader 构造函数接受文件名（README 示例 io::CSVReader<3> in("ram.csv")）
    io::CSVReader<2> reader(argv[1]);  // 2 columns
    reader.read_header(io::ignore_extra_column, "name", "value");
    Row row;
    int count = 0;
    while (reader.read_row(row.name, row.value)) {
        count++;
    }
    printf("fcpp smoke: rows=%d\n", count);
    return (count == 2) ? 0 : 1;
}
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    if not os.path.isfile(os.path.join(inc, "csv.h")):
        print(f"FAIL: csv.h header missing: {inc}", file=sys.stderr)
        return 1
    tmpdir = tempfile.mkdtemp(prefix="fcpp-smoke-")
    src = os.path.join(tmpdir, "smoke.cpp")
    csvf = os.path.join(tmpdir, "test.csv")
    binp = os.path.join(tmpdir, "smoke")
    try:
        with open(src, "w") as f:
            f.write(SMOKE_CPP)
        with open(csvf, "w") as f:
            f.write("name,value\na,1\nb,2\n")
        compiler = os.environ.get("FC_PARSE_CXX")
        if not compiler:
            target_compiler = "/data/service/hnp/bin/clang++"
            compiler = (target_compiler if os.path.exists(target_compiler)
                        else shutil.which("g++") or shutil.which("clang++"))
        if not compiler:
            print("FAIL: no C++ compiler found", file=sys.stderr)
            return 1
        r = subprocess.run(
            [compiler, src, "-o", binp,
             f"-I{inc}", "-std=c++11", "-lpthread"],
            capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL: compile smoke: {r.stderr}", file=sys.stderr)
            return 1
        r = subprocess.run([binp, csvf], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL: run smoke: {r.stderr}", file=sys.stderr)
            return 1
        print(r.stdout.strip())
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    print("OK: fast-cpp-csv-parser header + real CSVReader usage works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
