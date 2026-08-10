#!/usr/bin/env python3
"""Conan test_package for lha — binary tool smoke test (R34).

Verifies that the lha binary is installed and reports its version.
Uses test.sh to run the actual smoke test.
"""
import os

from conan import ConanFile


class LhaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_path = os.path.join(
            self.dependencies["lha"].package_folder, "bin", "lha"
        )
        self.run(f'"{bin_path}" --version', env="conanrun")
