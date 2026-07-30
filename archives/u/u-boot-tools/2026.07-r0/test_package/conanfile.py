#!/usr/bin/env python3
"""Conan test_package — u-boot-tools 2026.07-r0

Tests the mkimage binary by running --version.
u-boot-tools is a command-line tool suite, not a library,
so we test the binary directly.
"""
import os

from conan import ConanFile


class UbootToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for a binary tool test

    def test(self):
        bin_dir = self.dependencies["u-boot-tools"].cpp_info.bindirs[0]
        mkimage_bin = os.path.join(bin_dir, "mkimage")
        # Run mkimage --version to verify the binary works
        self.run(f'"{mkimage_bin}" --version', env="conanrun")
