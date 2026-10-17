#!/usr/bin/env python3
"""Conan test_package — partimage 0.6.9

Verifies the partimage binary is installed and runnable.
Runs `partimage --version` to confirm the binary works.
"""
from conan import ConanFile
from conan.tools.layout import basic_layout


class PartimageTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # partimage is installed to bin/, verify it runs
        # Using --version which is confirmed to work (CI L2 check)
        self.run("partimage --version", env="conanrun")
