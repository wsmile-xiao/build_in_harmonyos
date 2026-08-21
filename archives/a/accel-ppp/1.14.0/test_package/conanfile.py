#!/usr/bin/env python3
"""Conan entry point for the accel-ppp consumer smoke test."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class AccelPppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        package = self.dependencies[self.tested_reference_str].package_folder
        pppd = os.path.join(package, "bin", "accel-pppd")
        accel_cmd = os.path.join(package, "bin", "accel-cmd")
        test_script = os.path.join(self.source_folder, "smoke_test.py")
        self.run(f'python3 "{test_script}" "{pppd}" "{accel_cmd}"', env="conanrun")
