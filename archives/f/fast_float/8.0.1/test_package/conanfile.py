#!/usr/bin/env python3
"""Conan test_package for fast_float 8.0.1.

Compiles a consumer that parses a float with fast_float (from_chars
replacement) and verifies the parsed value.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building


class FastfloatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_cc(self):
        for cand in ("clang++", os.environ.get("CXX", "")):
            if cand and shutil.which(cand):
                return cand
        return "clang++"

    def build(self):
        incs = []
        for _r, _d in self.dependencies.items():
            incs += _d.cpp_info.includedirs
        inc = " ".join("-I" + p for p in dict.fromkeys(incs))
        cc = self._find_cc()
        self.run(f"{cc} -std=c++11 test_fast_float.cpp -o test_fast_float_probe {inc}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only verifying compile+link")
            return
        self.run("./test_fast_float_probe", env="conanrun")
