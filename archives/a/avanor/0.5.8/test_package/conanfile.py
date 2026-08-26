#!/usr/bin/env python3
"""Conan test_package — avanor 0.5.8 functional smoke test.

Delegates to test.sh, which verifies the avanor binary (existence, ELF
validity, aarch64 target) and runs the upstream automated game-test mode.
"""
import os
from conan import ConanFile


class AvanorTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["avanor"].package_folder
        avanor_bin = os.path.join(pkg_folder, "bin", "avanor")
        test_script = os.path.join(self.recipe_folder, "test.sh")
        self.run(f"sh {test_script} {avanor_bin}", env="conanrun")