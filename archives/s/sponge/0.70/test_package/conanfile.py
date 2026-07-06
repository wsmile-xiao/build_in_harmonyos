#!/usr/bin/env python3
"""Conan test_package — sponge 0.70

Tests the sponge binary by piping data through it.
sponge is a command-line tool, not a library, so we test the binary directly.
"""
import os

from conan import ConanFile


class SpongeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for a binary tool

    def test(self):
        # Get the bin path from the dependency's package
        bin_dir = self.dependencies["sponge"].cpp_info.bindirs[0]
        sponge_bin = os.path.join(bin_dir, "sponge")

        # Create test input file using Python file I/O
        input_file = os.path.join(self.build_folder, "sponge_input.txt")
        with open(input_file, "w") as f:
            f.write("hello from sponge\n")

        # Test 1: Basic write — soak up stdin and write to file
        outfile = os.path.join(self.build_folder, "sponge_out.txt")
        self.run(f'cat {input_file} | "{sponge_bin}" {outfile}', env="conanrun")
        self.run(f'cat {outfile}', env="conanrun")

        # Test 2: No args — stdin to stdout
        self.run(f'cat {input_file} | "{sponge_bin}"', env="conanrun")
