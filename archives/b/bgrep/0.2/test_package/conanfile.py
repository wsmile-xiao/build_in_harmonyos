#!/usr/bin/env python3
"""Conan test_package for bgrep 0.2 — Conan L1 official test.

bgrep is a CLI tool, so the test runs the binary directly
instead of linking against a library. The test creates a binary
file with a known hex pattern (DEADBEEF) and verifies bgrep
can find it at the correct offset.
"""
import os

from conan import ConanFile


class BgrepTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bgrep = os.path.join(
            self.dependencies["bgrep"].cpp_info.bindirs[0],
            "bgrep"
        )
        test_script = os.path.join(self.source_folder, "test_bgrep.py")
        self.run(f'python3 "{test_script}" "{bgrep}"', env="conanrun")
