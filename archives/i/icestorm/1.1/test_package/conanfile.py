#!/usr/bin/env python3
"""Run Project IceStorm command-line consumer checks."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class IcestormTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        bin_dir = os.path.join(self.dependencies["icestorm"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_icestorm.sh")
        self.run(f'sh "{script}" "{bin_dir}"', env="conanrun")
