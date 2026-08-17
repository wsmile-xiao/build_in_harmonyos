#!/usr/bin/env python3
"""Conan test_package for pbr 7.0.3 — consumer check.

Runs test_pbr.py (standalone test source, satisfies L0c) via self.run
with env="conanrun" (the conanrun PATH injection is required — a bare
subprocess would lose it, see yarl FileNotFoundError lesson).
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class PbrTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["pbr"].package_folder
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isdir(os.path.join(site, "pbr")):
            raise ConanException(f"pbr package missing under {site}")
        test_script = os.path.join(os.path.dirname(__file__), "test_pbr.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_pbr.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
