#!/usr/bin/env python3
"""Conan test_package — alloy-analyzer 6.2.0 (L1 test).

Tests the alloy wrapper end-to-end with real JVM execution:
  - package structure (wrapper + JAR)
  - `alloy version` prints 6.2.0
  - `alloy commands` lists the commands of an Alloy model
  - `alloy exec` solves an Alloy model and writes receipt.json + solutions

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile


class AlloyAnalyzerTestConan(ConanFile):
    """L1 test for alloy-analyzer — delegates to test.sh for smoke test logic."""
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Ensure a JDK is available for the wrapper (bishengjdk 17+).
        java_home = os.environ.get("JAVA_HOME", "")
        if not java_home or not os.path.isfile(os.path.join(java_home, "bin", "java")):
            for candidate in [
                os.path.expanduser("~/bishengjdk17"),
                os.path.expanduser("~/usr/local/bishengjdk17"),
            ]:
                if os.path.isfile(os.path.join(candidate, "bin", "java")):
                    java_home = candidate
                    break
        if java_home and os.path.isfile(os.path.join(java_home, "bin", "java")):
            os.environ["JAVA_HOME"] = java_home
            os.environ["PATH"] = os.path.join(java_home, "bin") + ":" + os.environ.get("PATH", "")

        # Get the alloy wrapper from the installed package
        alloy_bin = os.path.join(
            self.dependencies["alloy-analyzer"].package_folder, "bin", "alloy"
        )
        # Run the smoke test script (structure + version + commands + exec)
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{test_script}" "{alloy_bin}" "{self.build_folder}"',
                 env="conanrun")
