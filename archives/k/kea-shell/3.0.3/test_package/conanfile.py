#!/usr/bin/env python3
"""Conan consumer test for kea-shell 3.0.3."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class KeaShellTestConan(ConanFile):
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

        test_script = os.path.join(self.source_folder, "test_kea_shell.py")
        self.run(f'"{sys.executable}" "{test_script}"', env="conanrun")
