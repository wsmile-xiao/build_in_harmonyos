#!/usr/bin/env python3
"""Conan test_package — cpulimit 0.2

Verifies that the cpulimit binary is installed and runs correctly.
cpulimit is a command-line tool, so we test by running it directly.
"""
import os

from conan import ConanFile


class CpulimitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: Platform check — only run on Linux/OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            return

        # Get the cpulimit binary path from the dependency package
        cpulimit_bin = os.path.join(
            self.dependencies["cpulimit"].package_folder, "bin", "cpulimit"
        )

        # Verify binary exists
        assert os.path.isfile(cpulimit_bin), f"cpulimit binary not found at {cpulimit_bin}"

        # Run smoke test script (test.sh verifies cpulimit --help output)
        # No basic_layout: working directory is the test_package source folder
        self.run(f'CPULIMIT_BIN="{cpulimit_bin}" sh test.sh', env="conanrun")
