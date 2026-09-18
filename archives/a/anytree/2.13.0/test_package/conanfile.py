#!/usr/bin/env python3
"""Conan test_package for anytree 2.13.0 — consumer check.

Runs test_anytree.py (standalone test source, satisfies L0c) via self.run with
env="conanrun" so the conanrun PYTHONPATH injection is available.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class AnytreeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["anytree"].package_folder
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isdir(os.path.join(site, "anytree")):
            raise ConanException(f"anytree package missing under {site}")
        # sub-packages must survive packaging
        for sub in ("node", "iterators", "exporter", "importer", "util"):
            init = os.path.join(site, "anytree", sub, "__init__.py")
            if not os.path.isfile(init):
                raise ConanException(f"anytree sub-package '{sub}' missing ({init})")
        test_script = os.path.join(os.path.dirname(__file__), "test_anytree.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_anytree.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
