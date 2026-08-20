#!/usr/bin/env python3
"""Conan test_package for arm-none-eabi-gdb 15.1 — consumer check.

Runs test_armgdb.py (standalone test source, satisfies L0c) via self.run
with env="conanrun" (conanrun PATH injection required — see yarl lesson).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class ArmGdbTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["arm-none-eabi-gdb"].package_folder
        bindir = os.path.join(pkg, "bin")
        if not os.path.isfile(os.path.join(bindir, "arm-none-eabi-gdb")):
            raise ConanException(
                f"arm-none-eabi-gdb binary missing under {bindir}")
        test_script = os.path.join(os.path.dirname(__file__), "test_armgdb.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_armgdb.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{bindir}'", env="conanrun")
