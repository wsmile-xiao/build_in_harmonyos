#!/usr/bin/env python3
"""Conan test_package for gawk 5.3.0.

Smoke test for the gawk CLI tool.
Upstream has an extensive test suite (make check); this test_package
exercises the binary from a consumer perspective:
  1. gawk --version (binary runs, shows version)
  2. gawk arithmetic (exit code verifies correctness)
  3. gawk field processing (exit code verifies field extraction)
"""
import os

from conan import ConanFile


class GawkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Get the absolute path to the packaged gawk binary
        # This ensures the L1e negative test (R34) genuinely detects
        # dependency on the package — system awk won't be used.
        gawk_bin = os.path.join(self.dependencies["gawk"].package_folder,
                                "bin", "gawk")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'export GAWK_BIN="{gawk_bin}" && {bash} test.sh',
                 env="conanrun")
