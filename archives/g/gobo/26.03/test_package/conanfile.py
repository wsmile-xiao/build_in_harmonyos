#!/usr/bin/env python3
"""Conan test_package for Gobo Eiffel 26.03.

Verifies that the compiled Gobo tools (gec, geant, gelex, etc.)
can be executed and report valid version information.
"""
import os

from conan import ConanFile


class GoboTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify that key Gobo tools can be executed
        bin_dir = os.path.join(self.dependencies["gobo"].package_folder, "bin")
        tools = ["gec", "geant", "gelex", "geyacc", "gepp", "getest"]
        for tool in tools:
            tool_path = os.path.join(bin_dir, tool)
            self.run(f"{tool_path} --version", env="conanrun")
