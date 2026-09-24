#!/usr/bin/env python3
"""Conan test_package for iperf 2.2.1 — verifies the iperf binary works."""
from conan import ConanFile


class IperfTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: test executes the iperf binary from the package.
        self.run("sh test.sh", env="conanrun")
