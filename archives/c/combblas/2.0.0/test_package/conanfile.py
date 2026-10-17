#!/usr/bin/env python3
"""Conan test_package for CombBLAS 2.0.0.

Compiles a consumer that initializes MPI and creates a CombBLAS
distributed sparse matrix (public API), verifying link + runtime init.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building


class CombblasTestConan(ConanFile):
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
                        + ["-lCombBLAS", "-lmpi", "-lm", "-fopenmp"]
                        + ["-Wl,-rpath," + p for p in dict.fromkeys(libdirs)])
        cc = self._find_cc()
        self.run(f"{cc} -std=c++14 test_combblas.cpp -o test_combblas_probe {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only verifying compile+link")
            return
        # 直接运行（单进程 MPI_Init）：验证库链接 + 初始化
        self.run("./test_combblas_probe", env="conanrun")
