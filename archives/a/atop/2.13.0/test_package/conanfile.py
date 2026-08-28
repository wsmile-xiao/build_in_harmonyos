#!/usr/bin/env python3
"""Conan test_package for atop 2.13.0 — binary tool smoke test.

Verifies that the atop binary is installed and runs correctly.
"""
import os

from conan import ConanFile


class AtopTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the atop binary in the package
        atop_dir = self.dependencies["atop"].package_folder
        bin_path = os.path.join(atop_dir, "bin", "atop")
        if not os.path.exists(bin_path):
            # Try alternate path
            for root, dirs, files in os.walk(atop_dir):
                if "atop" in files:
                    bin_path = os.path.join(root, "atop")
                    break
        # Run the test shell script which executes atop -V
        test_script = os.path.join(self.source_folder, "test_atop.sh")
        os.chmod(test_script, 0o755)
        self.run(f'sh "{test_script}" "{bin_path}"', env="conanrun")
