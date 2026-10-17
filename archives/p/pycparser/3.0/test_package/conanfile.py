#!/usr/bin/env python3
"""Conan test_package for pycparser 3.0 — consumer check.

Runs test_pycparser.py (standalone test source, satisfies L0c) via self.run
with env="conanrun" so the conanrun PYTHONPATH injection is available.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class PycparserTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["pycparser"].package_folder
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isdir(os.path.join(site, "pycparser")):
            raise ConanException(f"pycparser package missing under {site}")
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_pycparser.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_pycparser.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
