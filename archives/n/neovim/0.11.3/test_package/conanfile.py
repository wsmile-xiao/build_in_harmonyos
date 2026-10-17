#!/usr/bin/env python3
"""Conan test_package for the Neovim headless spike."""

import os

from conan import ConanFile


class NeovimTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.source_folder, "test_headless.sh")
        self.run(f'sh "{script}"', env="conanrun")
