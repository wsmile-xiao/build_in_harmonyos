#!/usr/bin/env python3
"""Conan test_package — igtf-policy-bundle.

Verifies that the IGTF policy bundle package contains the expected
CA certificate trust anchors in PEM format.
"""
import os

from conan import ConanFile


class IGTFPolicyBundleTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["igtf-policy-bundle"].package_folder
        test_script = os.path.join(self.source_folder, "test_verify.py")
        self.run(f"python3 {test_script} {pkg_folder}", env="conanrun")