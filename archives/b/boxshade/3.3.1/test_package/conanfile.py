#!/usr/bin/env python3
"""Conan test_package for boxshade 3.3.1."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class BoxshadeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        boxshade = os.path.join(self.dependencies["boxshade"].package_folder, "bin", "boxshade")
        script = os.path.join(self.source_folder, "test_boxshade.sh")
        bash = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/data/service/hnp/bin/bash"
        self.run(f'BOXSHADE_BIN="{boxshade}" "{bash}" "{script}"', env="conanrun")
