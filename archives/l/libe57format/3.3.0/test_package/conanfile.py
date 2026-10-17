#!/usr/bin/env python3
"""Conan test_package for libe57format 3.3.0 — Conan L1 official test.

Builds two consumer executables against the installed package and runs
them: test_version (version API contract, 7 checks) and test_roundtrip
(write an 8-point scan + read it back with value verification, 13
checks). Both exit non-zero on any failure, so reaching the marker below
proves 2/2 passed.

Direct compile with the Conan-configured compiler (main-recipe pattern):
no CMake project() is executed, so the preflight "compiler identification
is unknown" failure mode cannot occur here either.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class Libe57formatTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _cxx(self):
        # Same rule as the main recipe (R33): compiler from the Conan conf,
        # never from a bare ${CXX} shell variable.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        path = compilers.get("cpp")
        if path and os.path.isfile(path):
            return path
        if path:
            return shutil.which(os.path.basename(path)) or path
        return shutil.which("clang++") or "clang++"

    def build(self):
        cxx = self._cxx()
        pkg = self.dependencies[self.tested_reference_str]
        pkg_inc = " ".join('"-I{0}"'.format(d) for d in pkg.cpp_info.includedirs)
        pkg_libdir = " ".join('"-L{0}"'.format(d) for d in pkg.cpp_info.libdirs)
        pkg_libs = " ".join('"-l{0}"'.format(l) for l in pkg.cpp_info.libs)
        if "xerces-c" not in self.dependencies:
            raise ConanException("dependency 'xerces-c' not in graph; cannot link")
        xerces = self.dependencies["xerces-c"]
        xerces_inc = " ".join('"-I{0}"'.format(d) for d in xerces.cpp_info.includedirs)
        xerces_libdir = " ".join('"-L{0}"'.format(d) for d in xerces.cpp_info.libdirs)
        xerces_libs = " ".join('"-l{0}"'.format(l) for l in xerces.cpp_info.libs)

        opt = "-O0 -g" if str(self.settings.build_type) == "Debug" else "-O2 -DNDEBUG"
        flags = "-std=c++14 -stdlib=libc++ -pthread {0}".format(opt)
        self.output.info("test_package compile with cxx={0}".format(cxx))
        for name in ("test_version", "test_roundtrip"):
            src = os.path.join(self.source_folder, name + ".cpp")
            if not os.path.isfile(src):
                raise ConanException("test source missing: {0}".format(src))
            out = os.path.join(self.build_folder, name)
            self.run('"{0}" {1} {2} {3} "{4}" {5} {6} {7} {8} -lpthread -lm'
                     ' -o "{9}"'.format(
                         cxx, flags, pkg_inc, xerces_inc, src,
                         pkg_libdir, pkg_libs, xerces_libdir, xerces_libs, out))

    def test(self):
        if not can_run(self):
            return
        # R5: OHOS has no /bin/sh — wrap execution with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        bindir = self.build_folder
        # Shared mode: consumer binaries load the installed .so from the
        # package cache (no RPATH emitted by the direct link); scope
        # LD_LIBRARY_PATH to these invocations only (never exported).
        run_prefix = ""
        try:
            is_shared = self.dependencies[self.tested_reference_str].options.shared
        except Exception:
            is_shared = False
        if is_shared:
            libdirs = self.dependencies[self.tested_reference_str].cpp_info.libdirs
            if libdirs:
                run_prefix = 'LD_LIBRARY_PATH="{0}" '.format(libdirs[0])
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "test_version + test_roundtrip",
            "discovered": 2,
            "passedCount": 2,
        }
        try:
            for name in ("test_version", "test_roundtrip"):
                proc = subprocess.run(
                    [bash, "-c", '{0}"{1}"'.format(
                        run_prefix, os.path.join(bindir, name))],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=600, cwd=bindir)
                self.output.info("=== {0} ===\n{1}".format(name, proc.stdout or ""))
                if proc.returncode != 0:
                    raise ConanException("{0} failed (rc={1})".format(name, proc.returncode))
        except Exception as exc:
            test_pkg["passed"] = False
            test_pkg["passedCount"] = 0
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg))
            raise
        # Both executables exited 0 above, each self-validates every
        # internal check, so 2/2 passed is proven here.
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg))
