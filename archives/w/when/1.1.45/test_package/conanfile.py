#!/usr/bin/env python3
"""Conan test_package for when — verifies the installed Perl calendar tool."""
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class WhenTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if can_run(self):
            self.run("when --version", env="conanrun")
