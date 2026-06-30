#!/usr/bin/env python3
"""Conan test_package for atasm 1.30 — terminal tool smoke test.

atasm is a command-line tool (not a library), so the test
assembles a simple .asm file to verify the binary works.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class AtasmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        atasm = os.path.join(self.dependencies["atasm"].package_folder, "bin", "atasm")
        # Create a minimal test .asm file in the build folder
        test_asm = os.path.join(self.build_folder, "test.asm")
        with open(test_asm, "w") as f:
            f.write("*= $F000\n .byte $AA, $55\n")
        test_bin = os.path.join(self.build_folder, "test.bin")
        # Assemble the test file — should succeed with exit code 0
        self.run(f'"{atasm}" -r -o"{test_bin}" "{test_asm}"', env="conanrun")
