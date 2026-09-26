#!/usr/bin/env python3
"""Conan consumer test for the nkt command-line application."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class NktTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning(
                "Skipping nkt runtime test in a non-runnable configuration"
            )
            return

        executable = os.path.join(
            self.dependencies["nkt"].package_folder, "bin", "nkt"
        )
        script = os.path.join(self.source_folder, "test_nkt.py")
        self.run(
            f'"{sys.executable}" "{script}" "{executable}" '
            f'"{self.build_folder}"',
            env="conanrun",
        )
