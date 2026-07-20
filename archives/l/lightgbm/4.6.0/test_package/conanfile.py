#!/usr/bin/env python3
"""Conan test_package for LightGBM 4.6.0."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class LightGBMTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["lightgbm"]
        candidates = [
            os.path.join(dep.package_folder, "bin", "lightgbm"),
            os.path.join(dep.package_folder, "bin", "lightgbm.exe"),
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                self.run(f'"{candidate}" --help || test $? -eq 255', env="conanrun")
                return
        raise Exception(f"lightgbm binary not found in package: {', '.join(candidates)}")
