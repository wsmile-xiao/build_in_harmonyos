#!/usr/bin/env python3
"""Conan test_package for fixed_math 2.2.0.

Compiles a consumer that uses the installed header-only library
(fixedmath::fixed_t + public math API) and runs it.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building


class FixedmathTestConan(ConanFile):
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
        # fixed_math 是 C++23 header-only 库（target_compile_features cxx_std_23）；
        # OHOS 工具链 clang 15 只认 C++23 草案拼写 -std=c++2b
        self.run(f"{cc} -std=c++2b test_fixed_math.cpp -o test_fixed_math_probe {inc}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only verifying compile+link")
            return
        self.run("./test_fixed_math_probe", env="conanrun")
