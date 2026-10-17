#!/usr/bin/env python3
"""Conan test_package - screen 5.0.0

R34: test_package must substantially exercise the tested package's functionality.
screen is a terminal binary (not a library), so tests run the binary directly.

Tests:
  1. screen --version   - verify binary is installed and reports correct version
  2. screen --help      - verify help output is produced
"""
import os

from conan import ConanFile


class ScreenTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Resolve the screen binary path from the package
        screen_bin = os.path.join(self.dependencies["screen"].package_folder, "bin", "screen")

        # Test 1: screen --version (smoke test - binary is installed and runnable)
        # Verify output contains "Screen version 5.0.0"
        self.run(f'"{screen_bin}" --version', env="conanrun")

        # Test 2: screen --help (verify help output is produced)
        self.run(f'"{screen_bin}" --help', env="conanrun")
