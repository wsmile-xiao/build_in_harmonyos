#!/usr/bin/env python3
"""End-to-end consumer test for the packaged SWFTools commands."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class SwftoolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        bin_dir = os.path.join(
            self.dependencies["swftools"].package_folder,
            "bin",
        )
        script = os.path.join(self.source_folder, "test_swftools.py")
        sample = os.path.join(self.source_folder, "smoke.sc")
        self.run(
            f'"{sys.executable}" "{script}" "{bin_dir}" "{sample}"',
            env="conanrun",
        )
