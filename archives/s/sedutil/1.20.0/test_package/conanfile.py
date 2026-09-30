#!/usr/bin/env python3
"""Conan test_package for sedutil 1.20.0 — binary tool smoke test.

Verifies that the sedutil-cli binary is installed and runs correctly.
"""
import os

from conan import ConanFile


class SedutilTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the sedutil-cli binary in the package
        bin_path = os.path.join(self.dependencies["sedutil"].package_folder, "sbin", "sedutil-cli")
        if not os.path.exists(bin_path):
            # Try alternate path
            for root, dirs, files in os.walk(self.dependencies["sedutil"].package_folder):
                if "sedutil-cli" in files:
                    bin_path = os.path.join(root, "sedutil-cli")
                    break
        # smoke test: scan for Opal compliant disks (rc=0, works without root)
        self.run(f'"{bin_path}" --scan', env="conanrun")
