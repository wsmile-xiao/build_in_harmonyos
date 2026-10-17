#!/usr/bin/env python3
"""Conan test_package for crasm 1.11."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class CrasmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        crasm = os.path.join(self.dependencies["crasm"].package_folder, "bin", "crasm")
        script = os.path.join(self.source_folder, "test_crasm.sh")
        bash = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/data/service/hnp/bin/bash"
        self.run(f'CRASM_BIN="{crasm}" "{bash}" "{script}"', env="conanrun")
