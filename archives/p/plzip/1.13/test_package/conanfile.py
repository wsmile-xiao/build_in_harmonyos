#!/usr/bin/env python3
"""Conan test_package for plzip — L1 test: compress + decompress round-trip.

Calls test_plzip.sh which:
1. Creates a test file with known content
2. Compresses it with the plzip binary
3. Decompresses the compressed file
4. Verifies the decompressed content matches the original using cmp
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class PlzipTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        bin_path = os.path.join(self.dependencies["plzip"].cpp_info.bindirs[0], "plzip")
        test_script = os.path.join(self.source_folder, "test_plzip.sh")

        # Run the round-trip test script
        self.run(
            f'sh "{test_script}" "{bin_path}" "{self.source_folder}"',
            env="conanrun",
        )
