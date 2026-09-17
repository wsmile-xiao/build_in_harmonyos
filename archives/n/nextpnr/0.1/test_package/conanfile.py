#!/usr/bin/env python3
"""Consumer test for the nextpnr package."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class NextpnrTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        bin_dir = os.path.join(self.dependencies["nextpnr"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_nextpnr.sh")
        self.run(f'sh "{script}" "{bin_dir}"', env="conanrun")
