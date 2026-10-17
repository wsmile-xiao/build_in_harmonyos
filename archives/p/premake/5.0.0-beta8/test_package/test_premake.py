#!/usr/bin/env python3
"""premake 5.0.0-beta8 test_package real test source (L0c: test source file).

Runs the installed premake5 binary: --version assertion + real project
generation smoke (generate gmake2 files from a small premake5.lua).
Usage: test_premake.py <path-to-premake5-bin>
"""
import os
import shutil
import subprocess
import sys
import tempfile

LUA = """workspace "smoke"
    configurations { "Debug", "Release" }
project "hello"
    kind "ConsoleApp"
    language "C"
    files { "hello.c" }
"""


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        sys.stderr.write(r.stdout)
        sys.stderr.write(r.stderr)
        raise AssertionError(f"command failed ({r.returncode}): {' '.join(cmd)}")
    return r


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_premake.py <premake5-bin>")
    pbin = sys.argv[1]
    if not os.path.isfile(pbin):
        raise AssertionError(f"premake5 binary missing: {pbin}")

    # 1) version assertion (binary runs on OHOS)
    r = run([pbin, "--version"])
    if "5.0.0" not in r.stdout and "5.0.0" not in r.stderr:
        raise AssertionError(f"unexpected version output: {r.stdout!r}")

    # 2) real project generation smoke (gmake2 backend)
    workdir = tempfile.mkdtemp(prefix="premake-tp-")
    try:
        with open(os.path.join(workdir, "premake5.lua"), "w") as f:
            f.write(LUA)
        with open(os.path.join(workdir, "hello.c"), "w") as f:
            f.write("int main(void){return 0;}\n")
        run([pbin, "gmake2"], cwd=workdir)
        makefile = os.path.join(workdir, "Makefile")
        if not os.path.isfile(makefile):
            raise AssertionError(f"generated Makefile missing: {makefile}")
        print("OK: premake 5.0.0-beta8 --version + gmake2 generation passed")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
