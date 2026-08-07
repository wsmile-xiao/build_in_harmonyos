#!/usr/bin/env python3
"""Conan test_package for chibicc 1.0.24.1."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class ChibiccTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        chibicc = os.path.join(self.dependencies["chibicc"].package_folder, "bin", "chibicc")
        script = os.path.join(self.source_folder, "test_chibicc.sh")
        shell = os.environ.get("CONFIG_SHELL") or "sh"
        self.run(f'CHIBICC_BIN="{chibicc}" "{shell}" "{script}"', env="conanrun")
