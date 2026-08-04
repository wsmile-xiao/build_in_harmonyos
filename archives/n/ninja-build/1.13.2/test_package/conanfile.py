#!/usr/bin/env python3
"""Conan test_package for ninja-build 1.13.2."""
import os
import sys

from conan import ConanFile


class NinjaBuildTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        exe_name = "ninja.exe" if self.settings.os == "Windows" else "ninja"
        ninja_path = os.path.join(
            self.dependencies["ninja-build"].package_folder,
            "bin",
            exe_name,
        )
        test_script = os.path.join(self.source_folder, "test_ninja.py")
        self.run(f'"{sys.executable}" "{test_script}" "{ninja_path}"', env="conanrun")
