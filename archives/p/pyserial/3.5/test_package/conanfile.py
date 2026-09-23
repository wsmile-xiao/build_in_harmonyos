#!/usr/bin/env python3
"""Conan consumer test for the pyserial package."""

from conan import ConanFile
import os
import sys


class PyserialTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        test_script = os.path.join(self.source_folder, "test_pyserial_consumer.py")
        package_folder = self.dependencies["pyserial"].package_folder
        self.run(
            f'{sys.executable} "{test_script}" "{package_folder}"',
            env="conanrun",
        )
