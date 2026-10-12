#!/usr/bin/env python3
"""Conan test_package for minunit — verifies header + real usage.

R34: include/minunit.h exists and a real compile+run of a MU_TEST_SUITE
(two cases) reports "2 tests, 2 assertions, 0 failures" and exits 0.
"""
import os
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SMOKE_C = r'''
#include <minunit.h>
#include <string.h>

MU_TEST(test_add) {
    mu_assert(2 + 2 == 4, "error, 2+2 != 4");
}

MU_TEST(test_str) {
    mu_assert(strcmp("a", "a") == 0, "error, strings differ");
}

MU_TEST_SUITE(test_suite) {
    MU_RUN_TEST(test_add);
    MU_RUN_TEST(test_str);
}

int main(void) {
    MU_RUN_SUITE(test_suite);
    MU_REPORT();
    return minunit_fail;
}
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package")
    parser.add_argument("--compiler")
    parser.add_argument("--signer")
    parser.add_argument("--work-root")
    args = parser.parse_args()
    pkg = args.package
    inc = os.path.join(pkg, "include")
    if not os.path.isfile(os.path.join(inc, "minunit.h")):
        print(f"FAIL: minunit.h header missing: {inc}", file=sys.stderr)
        return 1
    work_root = Path(args.work_root or os.environ.get("TMPDIR") or os.getcwd()).resolve()
    if not work_root.is_dir():
        print("FAIL: existing task work directory required", file=sys.stderr)
        return 1
    tmpdir = tempfile.mkdtemp(prefix="minunit-smoke-", dir=str(work_root))
    child_env = dict(os.environ, TMPDIR=tmpdir, TMPPREFIX=os.path.join(tmpdir, "tmp"))
    src = os.path.join(tmpdir, "smoke.c")
    binp = os.path.join(tmpdir, "smoke")
    try:
        with open(src, "w") as f:
            f.write(SMOKE_C)
        compiler = args.compiler
        if not compiler:
            target_compiler = "/data/service/hnp/bin/clang"
            compiler = (target_compiler if os.path.exists(target_compiler)
                        else shutil.which("gcc") or shutil.which("clang"))
        if not compiler:
            print("FAIL: no C compiler found", file=sys.stderr)
            return 1
        r = subprocess.run(
            [compiler, src, "-o", binp, f"-I{inc}", "-std=c11", "-lm"],
            capture_output=True, text=True, timeout=60, env=child_env)
        if r.returncode != 0:
            print(f"FAIL: compile smoke: {r.stderr}", file=sys.stderr)
            return 1
        ohos = hasattr(os, "uname") and os.uname().sysname == "HarmonyOS"
        signer = args.signer or (shutil.which("binary-sign-tool") if ohos else None)
        if ohos and not signer:
            print("FAIL: OHOS consumer requires a native signer", file=sys.stderr)
            return 1
        if signer:
            signed = binp + ".signed"
            subprocess.run([signer, "sign", "-inFile", binp, "-outFile", signed,
                            "-selfSign", "1"], check=True, timeout=30, env=child_env)
            os.chmod(signed, 0o700)
            binp = signed
        r = subprocess.run([binp], capture_output=True, text=True, timeout=10, env=child_env)
        if r.returncode != 0:
            print(f"FAIL: run smoke: {r.stdout} {r.stderr}", file=sys.stderr)
            return 1
        if "2 tests, 2 assertions, 0 failures" not in (r.stdout or ""):
            print(f"FAIL: unexpected test totals: {r.stdout}", file=sys.stderr)
            return 1
        print(r.stdout.strip())
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    print("OK: minunit.h header + real MU_TEST_SUITE runs and passes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
