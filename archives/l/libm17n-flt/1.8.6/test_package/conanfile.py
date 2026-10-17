#!/usr/bin/env python3
"""Conan consumer test for libm17n-flt 1.8.6 — m17n_flt_* API 冒烟。"""

import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pkg = self.dependencies["libm17n-flt"].package_folder
        cc = os.environ.get("CC", "clang")
        src = os.path.join(self.source_folder, "test_m17n_flt.c")
        self.run(
            f"{cc} -o test_m17n_flt {src} "
            f"-I{pkg}/include -L{pkg}/lib -lm17n-flt -lm17n-core -lm17n -lm",
            env="conanbuild",
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile and link only")
            return
        self.run("./test_m17n_flt", env="conanrun")
