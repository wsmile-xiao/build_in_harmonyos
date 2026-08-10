#!/usr/bin/env python3
"""Conan test_package for pigz 2.8 — runs the pigz binary to verify functionality.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

Test approach:
  1. Verify pigz --version outputs "pigz 2.8"
  2. Compress a test file with pigz
  3. Decompress the compressed file with pigz
  4. Verify the decompressed content matches the original
"""
import os

from conan import ConanFile


class PigzTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build needed — we run the pigz binary directly

    def test(self):
        # Find the pigz binary from the dependency package
        dep = self.dependencies["pigz"]
        bin_dir = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0])
        pigz_bin = os.path.join(bin_dir, "pigz")
        unpigz_bin = os.path.join(bin_dir, "unpigz")

        # Test 1: Verify pigz version
        self.run(f'"{pigz_bin}" --version', env="conanrun")

        # Test 2: Compress and decompress a file, verify round-trip
        test_file = os.path.join(self.build_folder, "test_input.txt")
        test_content = "Hello, pigz on HarmonyOS! This is a test file for round-trip compression."
        with open(test_file, "w") as f:
            f.write(test_content)

        # Compress (keep original with -k, force with -f)
        self.run(f'"{pigz_bin}" -kf "{test_file}"', env="conanrun")

        # Decompress
        gz_file = test_file + ".gz"
        self.run(f'"{pigz_bin}" -df "{gz_file}"', env="conanrun")

        # Verify content matches
        with open(test_file, "r") as f:
            result = f.read()
        assert result == test_content, f"Round-trip failed: expected '{test_content}', got '{result}'"

        # Test 3: Verify unpigz works (decompress)
        self.run(f'"{pigz_bin}" -kf "{test_file}"', env="conanrun")
        gz_file2 = test_file + ".gz"
        self.run(f'"{unpigz_bin}" -f "{gz_file2}"', env="conanrun")
        with open(test_file, "r") as f:
            result2 = f.read()
        assert result2 == test_content, "unpigz round-trip failed"
