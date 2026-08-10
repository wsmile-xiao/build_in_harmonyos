#!/usr/bin/env python3
"""Conan test_package — ca-certificates.

Verifies that the ca-certificates package contains the expected
Mozilla CA certificate bundle with valid PEM-format certificates
and the update-ca-certificates tool.
"""
import os

from conan import ConanFile


class CACertificatesTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["ca-certificates"].package_folder
        test_script = os.path.join(self.source_folder, "test_verify.py")
        self.run(f"python3 {test_script} {pkg_folder}", env="conanrun")
