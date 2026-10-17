#!/usr/bin/env python3
"""Conan test_package for dwz 0.16.

Verifies installed dwz binary exists and runs --version / -h.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class DwzTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["dwz"].package_folder
        bindir = os.path.join(pkg, "bin")
        dwz = os.path.join(bindir, "dwz")
        if not os.path.isfile(dwz):
            raise SystemExit("FAIL: dwz binary missing in bin/")
        self.output.info("OK: dwz present in bin/")
        script = os.path.join(self.recipe_folder, "test_dwz.sh")
        # L0c 真实测试源文件（test_dwz.sh）——通过 self.run() 执行
        self.run(f"sh {script} {bindir}", env="conanrun")
