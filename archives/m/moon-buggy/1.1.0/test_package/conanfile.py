#!/usr/bin/env python3
"""Conan test_package for moon-buggy 1.1.0."""
import os

from conan import ConanFile


class MoonBuggyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_path = os.path.join(
            self.dependencies["moon-buggy"].package_folder, "bin", "moon-buggy"
        )
        assert os.path.isfile(bin_path), f"moon-buggy binary not found: {bin_path}"
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(
            f'{bash} {os.path.join(self.source_folder, "test_moon_buggy.sh")} "{bin_path}" "1.1.0"',
            env="conanrun",
        )
