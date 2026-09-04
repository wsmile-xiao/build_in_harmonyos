#!/usr/bin/env python3
"""Conan test_package for sonic — runs the R34 consumer check.

L1 official test: verifies the packaged sonic CLI exists under <pkg>/bin/,
is a valid aarch64 ELF executable, runs (prints usage on no-args), and the
libsonic shared object is present under <pkg>/lib/. R34 real artifact
verification, not just file presence.
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
            pkg = self.dependencies["sonic"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_sonic.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}"',
                     env="conanrun")
