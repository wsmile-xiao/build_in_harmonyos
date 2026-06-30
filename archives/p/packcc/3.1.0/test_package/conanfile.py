#!/usr/bin/env python3
"""Conan test_package for packcc 3.1.0 — terminal tool smoke test.

packcc is a parser generator (executable), not a library.
This test verifies the binary runs and produces output.
"""
import os

from conan import ConanFile


class PackccTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # L2 smoke test: run the packcc binary directly
        bin_dir = self.dependencies["packcc"].cpp_info.bindirs[0]
        packcc_bin = os.path.join(bin_dir, "packcc")
        self.run(f'"{packcc_bin}" --version', env="conanrun")
