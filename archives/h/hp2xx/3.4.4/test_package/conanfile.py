#!/usr/bin/env python3
"""Consumer smoke tests for hp2xx."""

import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class Hp2xxTestConan(ConanFile):
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
        self.run(f'sh "{os.path.join(self.recipe_folder, "test.sh")}"', env="conanrun")
