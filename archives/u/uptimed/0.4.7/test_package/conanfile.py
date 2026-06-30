#!/usr/bin/env python3
"""Conan test_package — uptimed 0.4.7.

uptimed is a terminal utility (not a library). This test verifies
that the installed binaries are functional.
"""
import os

from conan import ConanFile


class UptimedTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the bin directory from the dependency
        dep = self.dependencies["uptimed"]
        bin_dir = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else "bin"
        bin_path = os.path.join(dep.package_folder, bin_dir, "uprecords")
        self.run(f'"{bin_path}" -v', env="conanrun")
