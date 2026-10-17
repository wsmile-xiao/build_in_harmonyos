#!/usr/bin/env python3
"""Conan test_package — perl-socket6 0.29

L1 test: verify package contains Socket6.pm and Socket6.so,
and attempt runtime module load via test_socket6.sh.
"""
import os

from conan import ConanFile


class PerlSocket6TestConan(ConanFile):
    settings = "os", "arch", "build_type", "compiler"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["perl-socket6"].package_folder

        # Run the smoke test script with the package folder
        test_script = os.path.join(os.path.dirname(__file__), "test_socket6.sh")
        self.run(f"sh {test_script} {pkg}")
