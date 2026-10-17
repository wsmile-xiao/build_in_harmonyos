#!/usr/bin/env python3
"""Conan test package for psutils 1.17."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class PsutilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies[self.tested_reference_str].package_folder
        shell = os.environ.get("CONFIG_SHELL", "sh")
        script = os.path.join(self.source_folder, "test_psutils.sh")
        self.run(f'"{shell}" "{script}" "{pkg}"', env="conanrun")
