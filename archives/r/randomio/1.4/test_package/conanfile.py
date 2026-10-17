#!/usr/bin/env python3
"""Conan test_package conanfile for randomio 1.4.

Runs the packaged benchmark end-to-end via test_randomio.py (see that file
for the assertions). The benchmark itself runs for ~1-2s (write-only traffic
against a preallocated regular file, one 1s sample).
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class RandomioTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    generators = "VirtualRunEnv"

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dep.package_folder, "bin")
        script = os.path.join(self.recipe_folder, "test_randomio.py")
        # R34: actually execute the tested package's binary.
        self.run(f'"{sys.executable}" "{script}" "{bindir}"', env="conanrun")
