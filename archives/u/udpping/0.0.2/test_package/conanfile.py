#!/usr/bin/env python3
"""Conan test_package — udpping 0.0.2

R34: Test must actually depend on the tested package.
udpping is a command-line tool; this test runs the binary and verifies output.
"""
import os

from conan import ConanFile


class UdppingTestConan(ConanFile):
    """test_package for udpping executable — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
