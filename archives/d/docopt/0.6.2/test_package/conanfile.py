#!/usr/bin/env python3
"""Conan test_package for docopt 0.6.2 — consumer check.

Runs test_docopt_consumer.py (standalone test source, satisfies L0c) via
self.run with env="conanrun" so the conanrun PYTHONPATH injection applies.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class DocoptTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["docopt"].package_folder
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isfile(os.path.join(site, "docopt.py")):
            raise ConanException(f"docopt.py missing under {site}")
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_docopt_consumer.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_docopt_consumer.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
