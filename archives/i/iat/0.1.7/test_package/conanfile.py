#!/usr/bin/env python3
"""Conan test_package — iat 0.1.7

Tests the iat binary by running 'iat --version' to verify it works.
iat is a command-line tool, not a library, so we test the binary directly.
"""
import os

from conan import ConanFile


class IatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        bin_dir = self.dependencies["iat"].cpp_info.bindirs[0]
        iat_bin = os.path.join(bin_dir, "iat")
        self.run(f'"{iat_bin}" --version', env="conanrun")
