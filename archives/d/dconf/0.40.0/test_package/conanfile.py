#!/usr/bin/env python3
"""Conan test_package for dconf — runs the R34 consumer check.

L1 official test: verifies the packaged dconf CLI tool exists under
<pkg>/bin/dconf and runs `dconf help` / `dconf --version`-style real
execution. R34 real artifact verification.
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["dconf"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_dconf.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}"',
                     env="conanrun")
