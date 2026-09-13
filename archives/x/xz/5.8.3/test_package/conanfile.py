#!/usr/bin/env python3
"""Conan test_package for xz 5.8.3 — consumer check (R34 substantive test).

Two independent installed-package consumers:
  1. test_xz.c  — compiles against the packaged liblzma headers + library and
                  performs a full LZMA easy-buffer-encode / stream-buffer-decode
                  round-trip on real data (core library API proof).
  2. test_xz.py — invokes the packaged `xz` CLI binary on a temp file:
                  compress -> decompress -> byte-compare round-trip (CLI proof).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class XzTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["xz"]
        inc = dep.cpp_info.includedirs[0]
        libdir = dep.cpp_info.libdirs[0]
        # 1) liblzma API round-trip consumer (compiled + executed)
        self.run(f"clang -o test_xz test_xz.c -I{inc} -L{libdir} -llzma", env="conanbuild")
        self.run("./test_xz", env="conanrun")
        # 2) packaged xz CLI round-trip consumer
        bindir = os.path.join(dep.package_folder, "bin")
        xz_bin = os.path.join(bindir, "xz")
        if not os.path.isfile(xz_bin):
            raise ConanException(f"xz binary missing: {xz_bin}")
        test_script = os.path.join(os.path.dirname(__file__), "test_xz.py")
        self.run(f"python3 '{test_script}' '{bindir}'", env="conanrun")
