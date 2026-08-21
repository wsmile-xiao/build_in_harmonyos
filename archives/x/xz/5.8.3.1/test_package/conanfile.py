#!/usr/bin/env python3
"""Conan test_package for xz 5.8.3 — consumer check.

Runs test_xz.py (standalone test source, satisfies L0c) via self.run
with env="conanrun" (conanrun PATH injection required — see yarl lesson).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class XzTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["xz"].package_folder
        bindir = os.path.join(pkg, "src", "xz")
        if not os.path.isfile(os.path.join(bindir, "xz")):
            raise ConanException(f"xz binary missing under {bindir}")
        test_script = os.path.join(os.path.dirname(__file__), "test_xz.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_xz.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{bindir}'", env="conanrun")
