#!/usr/bin/env python3
"""Conan test_package — DBI Perl XS module.

Verifies that the package contains the expected artifacts:
- .so file (shared library, valid ELF)
- .pm file (Perl module)
"""
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["perl-dbi"]
        pkg_folder = dep.package_folder

        self.output.info(f"Package folder: {pkg_folder}")

        test_script = os.path.join(os.path.dirname(__file__), "test_package.py")
        self.run(f'python3 "{test_script}" "{pkg_folder}"')
