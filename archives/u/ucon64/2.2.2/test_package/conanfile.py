#!/usr/bin/env python3
"""Conan test_package for ucon64 — terminal tool smoke test.

ucon64 is a command-line binary, not a library. This test verifies
that the binary is installed and can report its version (L2 smoke test).
"""
import os

from conan import ConanFile


class Ucon64TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # L2 smoke test: verify the binary runs and reports version
        bin_path = os.path.join(self.dependencies["ucon64"].package_folder, "bin", "ucon64")
        self.run(f'"{bin_path}" --version', env="conanrun")
