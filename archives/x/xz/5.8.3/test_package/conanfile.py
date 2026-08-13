#!/usr/bin/env python3
"""Conan test_package for xz 5.8.3 — tests xz binary + liblzma library.

Tests:
1. xz --version (binary smoke test)
2. LZMA compress/decompress round-trip via test_xz.c (library functional test)
"""
import os

from conan import ConanFile


class XzTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Direct compilation: link against liblzma from Conan package
        dep = self.dependencies["xz"]
        cpp = dep.cpp_info
        inc_flags = " ".join(f"-I{d}" for d in cpp.includedirs)
        lib_flags = " ".join(f"-L{d}" for d in cpp.libdirs)
        link_flags = " ".join(f"-l{l}" for l in cpp.libs)
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test_xz.c -o test_xz {inc_flags} {lib_flags} {link_flags}")

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        dep = self.dependencies["xz"]
        cpp = dep.cpp_info
        lib_dirs = ":".join(str(d) for d in cpp.libdirs)
        bin_dirs = ":".join(str(d) for d in cpp.bindirs)
        # Test xz binary (--version) — needs LD_LIBRARY_PATH for liblzma.so
        self.run(f"{bash} -c 'export PATH={bin_dirs}:$PATH; export LD_LIBRARY_PATH={lib_dirs}:$LD_LIBRARY_PATH; xz --version'", env="conanrun")
        # Test liblzma library (compress/decompress round-trip)
        self.run(f"{bash} -c 'export LD_LIBRARY_PATH={lib_dirs}:$LD_LIBRARY_PATH; ./test_xz'", env="conanrun")
