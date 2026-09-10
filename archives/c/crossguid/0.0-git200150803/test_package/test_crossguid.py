#!/usr/bin/env python3
"""Consumer smoke test for crossguid — compiles and runs real Guid API usage.

R34: must call the tested package's API (Guid string round-trip +
GuidGenerator::newGuid uniqueness), not a print-only stub.
Emits HMBS_TEST_PACKAGE_RESULT for the preflight gate.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

SMOKE_CPP = r'''
#include "guid.h"
#include <cassert>
#include <iostream>
#include <sstream>

int main() {
    // Case 1: string parse + stringify round-trip + equality
    Guid s1("7bcd757f-5b10-4f9b-af69-1a1f226f3b3e");
    Guid s4("7bcd757f-5b10-4f9b-af69-1a1f226f3b3e");
    Guid s2("16d1bd03-09a5-47d3-944b-5e326fd52d27");
    if (!(s1 == s4)) { std::cerr << "FAIL s1==s4" << std::endl; return 1; }
    if (!(s1 != s2)) { std::cerr << "FAIL s1!=s2" << std::endl; return 1; }
    std::stringstream ss;
    ss << s1;
    if (ss.str() != "7bcd757f-5b10-4f9b-af69-1a1f226f3b3e") {
        std::cerr << "FAIL round-trip: " << ss.str() << std::endl;
        return 1;
    }
    std::cout << "case1 round-trip ok: " << ss.str() << std::endl;

    // Case 2: newGuid generates distinct ids
    GuidGenerator gen;
    Guid r1 = gen.newGuid();
    Guid r2 = gen.newGuid();
    if (r1 == r2) { std::cerr << "FAIL newGuid not unique" << std::endl; return 1; }
    std::cout << "case2 newGuid ok: " << r1 << " != " << r2 << std::endl;
    return 0;
}
'''


def _compiler():
    # Prefer PATH lookup (hmbs prepends real tool dirs) over the possibly
    # stale /data/service/hnp absolute path; use the latter only if it
    # exists and PATH lookup failed. R33: no $CXX shell var.
    for c in ("clang++", "aarch64-linux-ohos-clang++", "c++", "g++"):
        _w = shutil.which(c)
        if _w:
            return _w
    for c in ("/data/service/hnp/bin/clang++",):
        if os.path.exists(c):
            return c
    return "clang++"


def main():
    if len(sys.argv) < 3:
        print("FAIL: usage test_crossguid.py <crossguid_pkg> <uuid_pkg>", file=sys.stderr)
        return 1
    crossguid_pkg, uuid_pkg = sys.argv[1], sys.argv[2]
    inc = os.path.join(crossguid_pkg, "include")
    if not os.path.isfile(os.path.join(inc, "guid.h")):
        print("FAIL: guid.h missing in %s" % inc, file=sys.stderr)
        return 1
    lib = os.path.join(crossguid_pkg, "lib", "libcrossguid.a")
    if not os.path.isfile(lib):
        so = os.path.join(crossguid_pkg, "lib", "libcrossguid.so")
        if os.path.isfile(so):
            lib = so
        else:
            print("FAIL: libcrossguid missing in %s" % crossguid_pkg, file=sys.stderr)
            return 1
    uuid_lib = os.path.join(uuid_pkg, "lib", "libuuid.a")
    uuid_inc = os.path.join(uuid_pkg, "include")
    tmpdir = tempfile.mkdtemp(prefix="crossguid-smoke-")
    src = os.path.join(tmpdir, "smoke.cpp")
    binp = os.path.join(tmpdir, "smoke")
    discovered = 2
    passed = 0
    try:
        with open(src, "w") as f:
            f.write(SMOKE_CPP)
        cxx = _compiler()
        cmd = [cxx, src, "-o", binp, "-std=c++11",
               "-I%s" % inc, "-I%s" % uuid_inc, lib]
        if os.path.isfile(uuid_lib):
            cmd.append(uuid_lib)
        else:
            cmd += ["-L%s" % os.path.join(uuid_pkg, "lib"), "-luuid"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            print("FAIL: compile smoke: %s" % (r.stderr[-2000:]), file=sys.stderr)
        else:
            r = subprocess.run([binp], capture_output=True, text=True, timeout=60)
            print((r.stdout or "") + (r.stderr or ""))
            if r.returncode == 0 and "case1" in (r.stdout or "") and "case2" in (r.stdout or ""):
                passed = 2
            else:
                print("FAIL: smoke run rc=%d" % r.returncode, file=sys.stderr)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    ok = (passed == discovered)
    print('HMBS_TEST_PACKAGE_RESULT=%s' % json.dumps({
        "executed": True,
        "passed": ok,
        "command": "python3 test_crossguid.py <crossguid_pkg> <uuid_pkg>",
        "discovered": discovered,
        "passedCount": passed,
    }))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
