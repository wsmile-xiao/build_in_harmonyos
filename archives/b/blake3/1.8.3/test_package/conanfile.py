#!/usr/bin/env python3
"""Conan test_package for blake3 1.8.3 — Conan L1 official test.

Uses direct compilation instead of CMake to keep test simple.
CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile


class Blake3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Direct compilation: link against blake3 from Conan package
        dep = self.dependencies["blake3"]
        cpp = dep.cpp_info
        inc_flags = " ".join(f"-I{d}" for d in cpp.includedirs)
        lib_flags = " ".join(f"-L{d}" for d in cpp.libdirs)
        link_flags = " ".join(f"-l{l}" for l in cpp.libs)
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test_blake3.c -o test_blake3 {inc_flags} {lib_flags} {link_flags}")

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_blake3'", env="conanrun")
