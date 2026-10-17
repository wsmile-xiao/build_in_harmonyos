#!/usr/bin/env python3
"""Conan test_package for nmrpflash 0.9.27."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class NmrpflashTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        bin_path = os.path.join(self.dependencies["nmrpflash"].package_folder, "bin", "nmrpflash")
        if not os.path.isfile(bin_path):
            raise Exception(f"nmrpflash binary not found: {bin_path}")

        # Run the smoke test script; call bash explicitly for portability
        self.run(f"bash {os.path.join(self.source_folder, 'test.sh')}", env="conanrun")