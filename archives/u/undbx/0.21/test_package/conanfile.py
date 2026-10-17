#!/usr/bin/env python3
"""Conan consumer test for the UnDBX command-line tool."""
import os

from conan import ConanFile


class UndbxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.source_folder, "test_undbx.sh")
        self.run(f'sh "{script}"', env="conanrun")
