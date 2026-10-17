#!/usr/bin/env python3
"""Conan test_package for sysstat 12.7.9 — binary smoke test."""
import os

from conan import ConanFile


class SysstatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # sysstat uses -V for version (not --version)
        bin_path = os.path.join(
            self.dependencies["sysstat"].package_folder, "bin", "sar"
        )
        self.run(f'"{bin_path}" -V', env="conanrun")
