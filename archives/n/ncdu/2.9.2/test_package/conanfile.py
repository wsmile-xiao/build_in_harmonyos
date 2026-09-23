#!/usr/bin/env python3
"""Conan consumer test for the ncdu command-line application."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class NcduTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning(
                "Skipping ncdu runtime test in a non-runnable configuration"
            )
            return

        executable = os.path.join(
            self.dependencies["ncdu"].package_folder, "bin", "ncdu"
        )
        script = os.path.join(self.source_folder, "test_ncdu.py")
        self.run(
            f'"{sys.executable}" "{script}" "{executable}" '
            f'"{self.build_folder}"',
            env="conanrun",
        )
