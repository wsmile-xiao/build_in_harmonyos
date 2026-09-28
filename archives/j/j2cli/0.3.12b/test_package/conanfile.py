#!/usr/bin/env python3
"""Consumer test: run j2cli through its installed console-script contract."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class J2cliTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            return
        dependency = self.dependencies["j2cli"]
        executable = os.path.join(dependency.package_folder, "bin", "j2")
        script = os.path.join(self.source_folder, "test_j2cli.py")
        self.run(f'"{sys.executable}" "{script}" "{executable}"', env="conanrun")
