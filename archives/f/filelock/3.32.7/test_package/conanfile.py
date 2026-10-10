#!/usr/bin/env python3
"""Conan test_package for filelock 3.32.7 — consumer check (R34).

Runs test_filelock.py (standalone test source, satisfies L0c) via self.run
with env="conanrun" so the conanrun PYTHONPATH injection is available.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class FilelockTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["filelock"].package_folder
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isfile(os.path.join(site, "filelock", "__init__.py")):
            raise ConanException(f"filelock missing under {site}")
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_filelock.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_filelock.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
