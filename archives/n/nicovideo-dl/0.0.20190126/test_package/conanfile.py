#!/usr/bin/env python3
"""Consumer test for the packaged nicovideo-dl command."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class NicovideoDlTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            return

        package_folder = str(self.dependencies["nicovideo-dl"].package_folder)
        test_script = os.path.join(
            self.source_folder,
            "test_nicovideo_dl.py",
        )
        self.run(
            f'"{sys.executable}" "{test_script}" "{package_folder}"',
            env="conanrun",
        )
