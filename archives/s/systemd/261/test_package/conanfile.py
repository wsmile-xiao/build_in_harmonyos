#!/usr/bin/env python3
"""Conan test_package for systemd — runs the R34 consumer check.

L1 official test: verifies the packaged libsystemd client library exists under
<pkg>/lib/, is a valid aarch64 ELF shared object, and the public header
sd-bus.h is present under <pkg>/include/. R34 real artifact verification.
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
            pkg = self.dependencies["systemd"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_systemd.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}"',
                     env="conanrun")
