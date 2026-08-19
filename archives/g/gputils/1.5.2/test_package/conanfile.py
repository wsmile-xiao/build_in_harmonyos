#!/usr/bin/env python3
"""Conan test_package for gputils 1.5.2 — consumer check.

Runs test_gputils.py (standalone test source, satisfies L0c) via self.run
with env="conanrun" (conanrun PATH injection required — see yarl lesson).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class GputilsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["gputils"].package_folder
        bindir = os.path.join(pkg, "gpasm")
        if not os.path.isfile(os.path.join(bindir, "gpasm")):
            raise ConanException(f"gpasm binary missing under {bindir}")
        test_script = os.path.join(os.path.dirname(__file__), "test_gputils.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_gputils.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{bindir}'", env="conanrun")
