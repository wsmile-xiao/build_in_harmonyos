#!/usr/bin/env python3
"""Conan consumer tests for pchar 1.5."""

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
        self.run("python3 test_pchar.py", cwd=self.source_folder, env="conanrun")
