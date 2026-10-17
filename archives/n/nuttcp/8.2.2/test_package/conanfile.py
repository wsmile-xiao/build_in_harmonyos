#!/usr/bin/env python3
"""Conan test_package for nuttcp 8.2.2.

Smoke test for the nuttcp CLI tool. Upstream has no formal test suite.
nuttcp -V prints version info and is used as the smoke test.
"""
from conan import ConanFile
from conan.tools.layout import basic_layout


class NuttcpTestConan(ConanFile):
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
        # nuttcp -V prints version "nuttcp-8.2.2" and exits 0.
        # This verifies the binary is functional and correctly built.
        self.run("nuttcp -V", env="conanrun")
