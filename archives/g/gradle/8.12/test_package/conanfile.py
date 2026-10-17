#!/usr/bin/env python3
"""Conan test_package — gradle 8.12 (L1 test).

Tests that the gradle wrapper script can print version information
and list available tasks on HarmonyOS.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile


class GradleTestConan(ConanFile):
    """L1 test for gradle — delegates to test.sh for smoke test logic."""
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the package folder — test.sh checks package structure
        # without requiring JAVA_HOME/bishengjdk.
        pkg_folder = self.dependencies["gradle"].package_folder
        # Run the structure test script
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{test_script}" "{pkg_folder}"',
                 env="conanrun")