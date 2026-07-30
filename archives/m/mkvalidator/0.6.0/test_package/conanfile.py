#!/usr/bin/env python3
"""Conan test_package for mkvalidator 0.6.0.

R34: Test must actually depend on the tested package.
mkvalidator is a CLI tool — the test runs the binary and checks version output.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class MkvalidatorTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Actually execute the tested binary
        dep = self.dependencies["mkvalidator"]
        mkvalidator_bin = os.path.join(dep.package_folder, "bin", "mkvalidator")
        test_script = os.path.join(self.source_folder, "test_mkvalidator.sh")
        if can_run(self):
            self.run(f'sh "{test_script}" "{mkvalidator_bin}"', env="conanrun")
