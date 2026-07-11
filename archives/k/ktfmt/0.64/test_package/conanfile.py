#!/usr/bin/env python3
"""Conan test_package — ktfmt 0.64 (L1 test).

Tests that the ktfmt wrapper script can format Kotlin source code
using the --google-style flag.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile


class KtfmtTestConan(ConanFile):
    """L1 test for ktfmt — delegates to test.sh for smoke test logic."""
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Ensure Java is available for the ktfmt wrapper script.
        # The build() phase may have auto-installed bishengjdk via cmd-pkgs,
        # but JAVA_HOME / PATH might not propagate to the test environment.
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

        # Get the ktfmt binary from the installed package
        ktfmt_bin = os.path.join(
            self.dependencies["ktfmt"].package_folder, "bin", "ktfmt"
        )
        # Run the smoke test script (version, help, google-style formatting)
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{test_script}" "{ktfmt_bin}" "{self.build_folder}"',
                 env="conanrun")
