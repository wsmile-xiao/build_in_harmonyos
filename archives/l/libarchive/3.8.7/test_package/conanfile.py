#!/usr/bin/env python3
"""Conan test_package for libarchive 3.8.7 — tests bsdtar binary + libarchive library.

Tests:
1. bsdtar --version (binary smoke test)
2. archive_read_open_memory + archive_read_next_header via test_libarchive.c
   (library functional test: create-in-memory tar read)
"""
import os

from conan import ConanFile


class LibarchiveTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Direct compilation: link against libarchive from Conan package
        dep = self.dependencies["libarchive"]
        cpp = dep.cpp_info
        inc_flags = " ".join(f"-I{d}" for d in cpp.includedirs)
        lib_flags = " ".join(f"-L{d}" for d in cpp.libdirs)
        link_flags = " ".join(f"-l{l}" for l in cpp.libs)
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test_libarchive.c -o test_libarchive {inc_flags} {lib_flags} {link_flags}")

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        dep = self.dependencies["libarchive"]
        cpp = dep.cpp_info
        lib_dirs = ":".join(str(d) for d in cpp.libdirs)
        bin_dirs = ":".join(str(d) for d in cpp.bindirs)
        # Test bsdtar binary (--version)
        self.run(f"{bash} -c 'export PATH={bin_dirs}:$PATH; export LD_LIBRARY_PATH={lib_dirs}:$LD_LIBRARY_PATH; bsdtar --version'", env="conanrun")
        # Test libarchive library (in-memory tar read)
        self.run(f"{bash} -c 'export LD_LIBRARY_PATH={lib_dirs}:$LD_LIBRARY_PATH; ./test_libarchive'", env="conanrun")