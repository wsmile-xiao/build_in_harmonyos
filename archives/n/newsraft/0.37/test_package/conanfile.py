#!/usr/bin/env python3
"""Conan test_package for newsraft 0.37."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class NewsraftTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        binary = os.path.join(
            self.dependencies["newsraft"].package_folder, "bin", "newsraft"
        )
        if not os.path.isfile(binary):
            raise Exception(f"newsraft binary not found: {binary}")

        self.run(
            f"bash {os.path.join(self.source_folder, 'test.sh')}",
            env="conanrun",
        )
