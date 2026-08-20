#!/usr/bin/env python3
"""Conan test_package for osv-scanner — verifies installed binaries work.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

The test verifies that the installed osv-scanner binary can execute
and report its version correctly.
"""
import os

from conan import ConanFile


class OsvScannerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # No build step needed — we test the pre-built binary
        pass

    def test(self):
        # Get the bin directory from the dependency's package folder
        dep = self.dependencies["osv-scanner"]
        bin_dir = os.path.join(dep.package_folder, "bin")

        osv_scanner = os.path.join(bin_dir, "osv-scanner")
        osv_reporter = os.path.join(bin_dir, "osv-reporter")

        # Test osv-scanner
        self.run(f'"{osv_scanner}" --version', env="conanrun")

        # Test osv-reporter
        self.run(f'"{osv_reporter}" --version', env="conanrun")
