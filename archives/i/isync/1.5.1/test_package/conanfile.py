#!/usr/bin/env python3
"""test_package for isync — runs mbsync --version to verify the binary."""
import os

from conan import ConanFile


class IsyncTestConan(ConanFile):
    """Smoke test: verify mbsync binary is installed and reports version."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} test.sh", env="conanrun")
