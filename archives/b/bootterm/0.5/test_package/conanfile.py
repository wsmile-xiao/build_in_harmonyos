#!/usr/bin/env python3
"""Conan test_package for bootterm 0.5 — Conan L1 official test.

bootterm is a CLI tool, so the test runs the produced binary directly.
The test verifies real behavior of `bt`:
  1. Binary exists and is executable
  2. -V prints the BootTerm version banner and license line
  3. -h prints the full usage message
  4. -l lists serial ports (empty table) and exits 0
"""
import os

from conan import ConanFile


class BoottermTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bt = os.path.join(
            self.dependencies["bootterm"].cpp_info.bindirs[0],
            "bt",
        )
        test_script = os.path.join(self.source_folder, "test_bootterm.py")
        self.run(f'python3 "{test_script}" "{bt}"', env="conanrun")
