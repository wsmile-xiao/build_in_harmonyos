#!/usr/bin/env python3
"""Conan test_package — Encode::JIS2K Perl XS module.

Verifies that the package contains the expected artifacts:
- JIS2K.so (shared library, valid ELF)
- JIS2K.pm (Perl module file with version 0.05)
- Attempts to load the Perl module and test encode/decode (R34)
"""
import os

from conan import ConanFile


class PerlEncodeJIS2KTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get package folder from dependency
        dep = self.dependencies["perl-encode-jis2k"]
        pkg_folder = dep.package_folder

        self.output.info(f"Package folder: {pkg_folder}")

        # Paths to verify
        so_path = os.path.join(pkg_folder, "lib", "auto", "Encode", "JIS2K", "JIS2K.so")
        pm_path = os.path.join(pkg_folder, "lib", "Encode", "JIS2K.pm")
        lib_dir = os.path.join(pkg_folder, "lib")

        # Run the test script with paths as arguments
        test_script = os.path.join(os.path.dirname(__file__), "test_package.py")
        self.run(f'python3 "{test_script}" "{so_path}" "{pm_path}" "{lib_dir}"')
