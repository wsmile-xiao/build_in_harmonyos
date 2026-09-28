#!/usr/bin/env python3
"""Conan test_package for sgmllib3k 1.0.0 — consumer check (R34)."""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class Sgmllib3kTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["sgmllib3k"].package_folder
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isfile(os.path.join(site, "sgmllib.py")):
            raise ConanException(f"sgmllib.py missing under {site}")
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_sgmllib3k.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_sgmllib3k.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
