#!/usr/bin/env python3
"""Consumer test for the packaged mistune API."""
import os
import sys

from conan import ConanFile


class MistuneTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.source_folder, "test_mistune.py")
        self.run(f'"{sys.executable}" "{script}"', env="conanrun")
