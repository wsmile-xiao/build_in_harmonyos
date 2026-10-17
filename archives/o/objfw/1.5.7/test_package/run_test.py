#!/usr/bin/env python3
"""Compile and run the ObjFW Objective-C consumer test.

Called by test_package/conanfile.py test(). Compiles test_package.m with
the ObjFW runtime flags (mirroring cpp_info.objcflags) and executes the
resulting binary; a non-zero exit code (or any subprocess failure) is
propagated so conan treats it as a test failure.
"""

import os
import shutil
import subprocess
import sys


def _find_compiler() -> str:
    """Locate clang: honor $CC (conanbuild exports it), else search PATH.

    The CI test stage does not inherit the build environment PATH, so a
    bare "clang" lookup fails with FileNotFoundError; probing common
    locations keeps the driver runnable under conanbuild and conanrun.
    """
    cc = os.environ.get("CC", "")
    if cc and shutil.which(cc):
        return cc
    for cand in ("clang", "/data/service/hnp/bin/clang",
                 "/usr/bin/clang", "/usr/local/bin/clang"):
        if shutil.which(cand) or os.access(cand, os.X_OK):
            return cand
    raise RuntimeError("clang not found (set CC or add it to PATH)")


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "test_package.m")
    out = os.path.join(here, "test_package_bin")

    # Package layout is passed by the conan recipe via environment variables
    # (OBJFW_INCLUDE_DIR / OBJFW_LIB_DIR) so this driver stays recipe-agnostic.
    includedir = os.environ.get("OBJFW_INCLUDE_DIR", "")
    libdir = os.environ.get("OBJFW_LIB_DIR", "")
    if not includedir or not libdir:
        print("OBJFW_INCLUDE_DIR/OBJFW_LIB_DIR not set", file=sys.stderr)
        return 2

    cc = _find_compiler()
    cmd = [
        cc, "-x", "objective-c",
        "-fobjc-runtime=objfw",
        "-fconstant-string-class=OFConstantString",
        "-I" + includedir,
        src, "-o", out,
        "-L" + libdir, "-lobjfw", "-lobjfwrt", "-lobjfwtls",
        "-Wl,-rpath," + libdir,
    ]
    print("+ " + " ".join(cmd))
    compile_rc = subprocess.call(cmd)
    if compile_rc != 0:
        print("compile failed: rc=%d" % compile_rc, file=sys.stderr)
        return 3

    run_rc = subprocess.call([out])
    if run_rc != 0:
        print("test_package_bin failed: rc=%d" % run_rc, file=sys.stderr)
        os.remove(out)
        return run_rc

    os.remove(out)
    print("objfw test_package: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
