#!/usr/bin/env python3
"""Conan test_package for pchar 1.5 (network path characterization tool).

pchar probes a destination host with ICMP/UDP/TCP probes and prints RTT /
jitter / loss statistics. The test runs the installed binary with its
version and help flags (both exit 0), which exercises the built binary
without requiring network access.
"""

from conan import ConanFile
from conan.tools.layout import basic_layout


class PcharTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        pass

    def test(self):
        # Test 1: --version must print the version and exit 0
        self.run("pchar --version", env="conanrun")

        # Test 2: --help must print the usage and exit 0
        self.run("pchar --help", env="conanrun")
