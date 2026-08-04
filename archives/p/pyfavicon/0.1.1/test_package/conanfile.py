#!/usr/bin/env python3
"""Conan consumer test for pyfavicon 0.1.1."""

import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class PyfaviconTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def test(self):
        test_script = os.path.join(self.source_folder, "test_pyfavicon.py")
        self.run(f'"{sys.executable}" "{test_script}"', env="conanrun")
