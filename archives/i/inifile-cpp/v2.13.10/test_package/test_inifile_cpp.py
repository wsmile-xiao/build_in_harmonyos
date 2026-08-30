#!/usr/bin/env python3
"""inifile-cpp consumer test (R34): header exists + real ini::IniFile usage
(compile+run smoke — decode/encode round-trip via the packaged header)."""
import os
import subprocess
import sys
import tempfile

SMOKE_CPP = r'''
#include <inicpp.h>
#include <iostream>
#include <sstream>

int main() {
    // 真实 API 使用：decode + 读取字段 + encode 往返
    std::istringstream ss("[Foo]\nbar=hello world\n[Test]");
    ini::IniFile inif;
    inif.decode(ss);
    if (inif.size() != 2) { std::cout << "FAIL: size\n"; return 1; }
    if (inif["Foo"]["bar"].as<std::string>() != "hello world") {
        std::cout << "FAIL: bar value\n"; return 1;
    }
    std::ostringstream os;
    inif.encode(os);
    if (os.str().find("hello world") == std::string::npos) {
        std::cout << "FAIL: encode round-trip\n"; return 1;
    }
    std::cout << "OK: inifile-cpp decode/read/encode works\n";
    return 0;
}
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    hdr = os.path.join(inc, "inicpp.h")
    if not os.path.isfile(hdr):
        print(f"FAIL: inicpp.h missing: {hdr}", file=sys.stderr)
        return 1
    tmpdir = tempfile.mkdtemp(prefix="inifile-cpp-")
    src = os.path.join(tmpdir, "smoke.cpp")
    binp = os.path.join(tmpdir, "smoke")
    try:
        with open(src, "w") as f:
            f.write(SMOKE_CPP)
        cxx = "/data/service/hnp/bin/clang++"
        if not os.path.isfile(cxx):
            cxx = "clang++"
        r = subprocess.run([cxx, src, "-o", binp, f"-I{inc}",
                            "-std=c++11"],
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
    print("OK: inifile-cpp header + ini::IniFile real API works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
