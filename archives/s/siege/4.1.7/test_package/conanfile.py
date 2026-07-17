#!/usr/bin/env python3
"""Conan test_package for siege 4.1.7."""
import os

from conan import ConanFile


class SiegeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        siege_bin = os.path.join(
            self.dependencies["siege"].cpp_info.bindirs[0],
            "siege",
        )
        self.run(f'"{siege_bin}" --version', env="conanrun")
