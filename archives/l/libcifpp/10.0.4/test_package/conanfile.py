#!/usr/bin/env python3
"""Conan test_package for libcifpp 10.0.4.

Compiles a consumer that creates a cif::file (public API) and verifies
link + runtime init (R34: 真实执行).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building


class LibcifppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_cc(self):
        for cand in ("clang++", os.environ.get("CXX", "")):
            if cand and shutil.which(cand):
                return cand
        return "clang++"

    def build(self):
        incs, libdirs = [], []
        for _r, _d in self.dependencies.items():
            incs += _d.cpp_info.includedirs
            libdirs += _d.cpp_info.libdirs
        inc = " ".join("-I" + p for p in dict.fromkeys(incs))
        link = " ".join(["-L" + p for p in dict.fromkeys(libdirs)]
                        + ["-lcifpp", "-lpcre2-8", "-lfmt", "-lz", "-lm"]
                        + ["-Wl,-rpath," + p for p in dict.fromkeys(libdirs)])
        cc = self._find_cc()
        self.run(f"{cc} -std=c++20 test_cifpp.cpp -o test_cifpp_probe {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only verifying compile+link")
            return
        self.run("./test_cifpp_probe", env="conanrun")
