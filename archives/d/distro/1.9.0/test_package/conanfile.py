#!/usr/bin/env python3
"""Conan test_package for distro 1.9.0 — Conan L1 official test.

distro is a pure-Python package. The test directly runs a Python checker to
verify the installed module comes from the Conan package and reports the
expected version and API behavior.

CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile


class DistroTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Import explicitly from the package under test. This prevents a
        # same-named module installed on the host from masking the dependency.
        package = self.dependencies["distro"].package_folder
        site = os.path.join(package, "lib", "python3.12", "site-packages")
        checker = os.path.join(os.path.dirname(__file__), "verify_distro.py")
        self.run(f'python3 "{checker}" "{site}"')
