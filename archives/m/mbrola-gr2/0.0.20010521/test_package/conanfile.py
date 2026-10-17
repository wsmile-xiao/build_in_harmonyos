#!/usr/bin/env python3
"""Conan consumer test for the packaged MBROLA GR2 voice database."""

import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class MbrolaGr2TestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies["mbrola-gr2"].package_folder
        script = os.path.join(self.source_folder, "test_mbrola_voice.py")
        self.run(
            f'"{sys.executable}" "{script}" "{package_folder}"',
            env="conanrun",
        )
