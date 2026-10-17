#!/usr/bin/env python3
"""PHP Enchant module consumer tests on the target platform."""
import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


class TestPhpEnchant(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("php/8.5.8", run=True)

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if can_run(self):
            php = os.path.join(self.dependencies["php"].package_folder, "bin", "php")
            module = os.path.join(self.dependencies["php85-enchant"].package_folder, "lib", "php", "extensions", "enchant.so")
            test = os.path.join(self.source_folder, "test.sh")
            self.run(f"bash {shlex.quote(test)} {shlex.quote(php)} {shlex.quote(module)}", env="conanrun")
