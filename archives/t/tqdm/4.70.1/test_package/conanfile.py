#!/usr/bin/env python3
"""Conan test_package for tqdm 4.70.1 — consumer check (R34)."""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class TqdmTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["tqdm"].package_folder
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isfile(os.path.join(site, "tqdm", "_tqdm.py")):
            raise ConanException(f"tqdm missing under {site}")
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_tqdm.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_tqdm.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
