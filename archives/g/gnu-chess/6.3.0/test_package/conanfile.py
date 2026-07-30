#!/usr/bin/env python3
"""Run GNU Chess command-line and UCI protocol checks."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class GnuChessTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        binary = os.path.join(
            self.dependencies["gnu-chess"].package_folder, "bin", "gnuchess"
        )
        smoke_test = os.path.join(self.source_folder, "test_gnuchess.sh")

        self.run(f'sh "{smoke_test}" "{binary}"', env="conanrun")
