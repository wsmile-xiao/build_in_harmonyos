#!/usr/bin/env python3
"""Conan recipe — debugbreak 1.0 (header-only C/C++ library).

debugbreak lets you put breakpoints in C/C++ code with a call to
debug_break(). The library is a single header (debugbreak.h); the
upstream GNUmakefile builds the gdb-driven test programs (test/break.c,
test/break-c++.cc, test/fib.c, test/trap.c). No configure script is
shipped, so the header is packaged as-is and the upstream test programs
are compiled against the OHOS toolchain as the build-time adaptation
check (C and C++ consumers both exercised).
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class DebugbreakConan(ConanFile):
    name = "debugbreak"
    version = "1.0"
    description = "Put breakpoints in C/C++ code with a call to debug_break()"
    license = "BSD-2-Clause"
    homepage = "https://github.com/scottt/debugbreak"
    url = "https://github.com/scottt/debugbreak"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compilers(self):
        """R33: compilers come from the profile conf, not shell env vars."""
        conf = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = conf.get("c") or "clang"
        cxx = conf.get("cpp") or "clang++"
        return cc, cxx

    def build(self):
        # Compile the four upstream test programs (C and C++) to prove the
        # header builds and links on OHOS with the same toolchain as CI.
        cc, cxx = self._compilers()
        src = self.source_folder
        out = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(out, exist_ok=True)
        tests = [
            (cc, "test/break.c", "break"),
            (cc, "test/fib.c", "fib"),
            (cc, "test/trap.c", "trap"),
            (cxx, "test/break-c++.cc", "break-c++"),
        ]
        for compiler, rel_src, name in tests:
            cmd = [compiler, "-Os", "-Wall", "-I", src,
                   os.path.join(src, rel_src), "-o", os.path.join(out, name)]
            self.output.info("upstream test build: " + " ".join(cmd))
            proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, timeout=600)
            if proc.returncode != 0:
                raise RuntimeError(f"failed to compile {rel_src}:\n{proc.stdout}")

    def package(self):
        copy(self, "debugbreak.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "debugbreak-gdb.py", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "debugbreak"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "debugbreak")
        self.cpp_info.set_property("cmake_target_name", "debugbreak::debugbreak")
        self.cpp_info.includedirs = ["include"]
