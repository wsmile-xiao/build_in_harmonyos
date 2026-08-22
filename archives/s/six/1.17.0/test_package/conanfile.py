#!/usr/bin/env python3
"""Consumer test for the packaged six compatibility module."""

import os
import sys

from conan import ConanFile


class SixTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        test_script = os.path.join(self.source_folder, "test_six.py")
        self.run(f'"{sys.executable}" "{test_script}"', env="conanrun")
