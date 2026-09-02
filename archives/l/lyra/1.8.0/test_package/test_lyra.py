#!/usr/bin/env python3
"""Conan test_package for lyra — verifies headers present + real usage.

R34: include/lyra/lyra.hpp exists and a real compile+run using lyra works
(lyra::cli parse a positional arg and a flag).
"""
import os
import subprocess
import sys
import tempfile

SMOKE_CPP = r'''
#include <lyra/lyra.hpp>
#include <cstdio>
#include <string>
int main(int argc, char** argv) {
    using namespace lyra;
    std::string name;
    bool verbose = false;
    auto cli = lyra::cli()
        | opt(verbose)["-v"]["--verbose"]("verbose flag")
        | arg(name, "name")("input name");
    auto result = cli.parse({ argc, argv });
    if (!result) {
        std::fprintf(stderr, "FAIL parse: %s\n", result.message().c_str());
        return 1;
    }
    std::printf("lyra smoke: name=%s verbose=%d\n",
                name.c_str(), verbose ? 1 : 0);
    return name == "hello" ? 0 : 2;
}
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    if not os.path.isfile(os.path.join(inc, "lyra", "lyra.hpp")):
        print(f"FAIL: lyra/lyra.hpp header missing: {inc}", file=sys.stderr)
        return 1
    tmpdir = tempfile.mkdtemp(prefix="lyra-smoke-")
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
        r = subprocess.run([binp, "-v", "hello"], capture_output=True,
                           text=True)
        if r.returncode != 0:
            print(f"FAIL: run smoke: {r.returncode}: {r.stderr}",
                  file=sys.stderr)
            return 1
        print(r.stdout.strip())
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
    print("OK: lyra headers + real lyra::cli usage works")
    return 0


if __name__ == "__main__":
    sys.exit(main())