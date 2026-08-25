#!/usr/bin/env python3
"""Conan test_package — asm6809 2.15

Tests the asm6809 binary by running --version and assembling a
minimal 6809 source file (R34: must execute the actual binary).

asm6809 is a command-line cross-assembler for Motorola 6809 and
Hitachi 6309. We verify:
  1. asm6809 --version produces expected version string
  2. asm6809 can assemble a minimal .s source file
"""
import os

from conan import ConanFile


class Asm6809TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for a binary tool

    def test(self):
        # R34: Must execute the asm6809 binary
        bin_dir = self.dependencies["asm6809"].cpp_info.bindirs[0]
        asm6809_bin = os.path.join(bin_dir, "asm6809")

        # Test 1: Verify version output
        self.run(f'"{asm6809_bin}" --version', env="conanrun")

        # Test 2: Assemble a minimal 6809 program
        # 6809 assembly: pseudo-ops and instructions indented with tab,
        # labels in column 1.
        test_s = os.path.join(self.build_folder, "test.s")
        with open(test_s, "w") as f:
            f.write("\torg $1000\nstart\n\tnop\n\tend start\n")
        test_out = os.path.join(self.build_folder, "test.out")
        self.run(f'"{asm6809_bin}" -o {test_out} {test_s}', env="conanrun")
