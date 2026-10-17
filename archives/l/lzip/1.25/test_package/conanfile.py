#!/usr/bin/env python3
"""Conan test_package for lzip 1.25.

lzip is a command-line compression tool. This test verifies:
1. The binary exists and reports its version
2. Compression + decompression roundtrip produces identical output
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class LzipTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # VirtualRunEnv adds lzip's bin dir to PATH
            # Test 1: version check
            self.run("lzip --version", env="conanrun")
            # Test 2: compression/decompression roundtrip via test_lzip.sh
            test_dir = self.source_folder
            # Clean up any leftover files from previous runs
            for fname in ["test_input.txt", "test_input.txt.lz", "test_output.txt"]:
                fpath = os.path.join(test_dir, fname)
                if os.path.exists(fpath):
                    os.remove(fpath)
            # Run the test script
            self.run(f'sh "{os.path.join(test_dir, "test_lzip.sh")}"', env="conanrun")
