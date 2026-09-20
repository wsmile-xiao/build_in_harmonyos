#!/usr/bin/env python3
"""Conan test_package for tio 3.9-r0."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class TioTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Skipping runtime tests while cross-compiling")
            return

        binary = os.path.join(self.dependencies["tio"].package_folder, "bin", "tio")
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{script}" "{binary}"', env="conanrun")
