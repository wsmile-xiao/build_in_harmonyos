#!/usr/bin/env python3
"""Conan consumer test for starfetch 0.0.4."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class StarfetchTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        test_script = os.path.join(self.source_folder, "test_starfetch.py")
        self.run(f'"{sys.executable}" "{test_script}"', env="conanrun")
