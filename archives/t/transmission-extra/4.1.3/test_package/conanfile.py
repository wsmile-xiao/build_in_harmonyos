#!/usr/bin/env python3
"""Conan test package for installed Transmission 4.1.3 CMake utilities."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class TransmissionExtraTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: utilities packaged but cannot run")
            return
        package_folder = self.dependencies["transmission-extra"].package_folder
        script = os.path.join(self.source_folder, "test_tools.py")
        self.run(f'python3 "{script}" "{package_folder}"', env="conanrun")
