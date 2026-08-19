#!/usr/bin/env python3
"""Conan test_package for fontconfig 2.18.3 — consumer check.

Runs test_fontconfig.py (standalone test source, satisfies L0c) via
self.run with env="conanrun".
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class FontconfigTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["fontconfig"].package_folder
        bd = os.path.join(pkg, "bin")
        if not os.path.isdir(bd):
            raise ConanException(f"bin missing under {pkg}")
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_fontconfig.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_fontconfig.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{bd}'", env="conanrun")
