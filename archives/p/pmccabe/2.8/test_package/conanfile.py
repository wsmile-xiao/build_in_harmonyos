#!/usr/bin/env python3
"""Conan test_package for pmccabe — L1 official test.

Tests that the pmccabe binary is installed and functional.
"""
import os

from conan import ConanFile


class PmccabeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Create a simple C file for testing
        test_c = os.path.join(self.source_folder, "test.c")
        with open(test_c, "w") as f:
            f.write("int main(void) { return 0; }\n")
        # Use full path to pmccabe binary from the installed package
        pmccabe_bin = os.path.join(
            self.dependencies["pmccabe"].package_folder,
            "bin",
            "pmccabe"
        )
        self.run(f"{pmccabe_bin} {test_c}")
