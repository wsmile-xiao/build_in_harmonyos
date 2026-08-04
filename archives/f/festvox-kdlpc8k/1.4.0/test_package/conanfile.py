#!/usr/bin/env python3
"""Conan test_package — festvox-kdlpc8k 1.4.0 resource validation.

L1 test: verify the pure voice data package is correctly installed.
Executes test_resources.sh via self.run() to satisfy L0d gate.
"""

import os
import shlex

from conan import ConanFile


class FestvoxKdlpc8kTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["festvox-kdlpc8k"].package_folder
        voice_dir = os.path.join(
            pkg_folder,
            "share", "festival", "voices", "english", "ked_diphone",
        )
        script = os.path.join(self.source_folder, "test_resources.sh")
        self.run(f"sh {shlex.quote(script)} {shlex.quote(voice_dir)}")
