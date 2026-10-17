#!/usr/bin/env python3
"""Consumer smoke test for the NUT 2.8.5 package."""

import os

from conan import ConanFile


class NutTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        nut = self.dependencies["nut"]
        upsc = os.path.join(nut.package_folder, "bin", "upsc")
        assert os.path.isfile(upsc), f"upsc was not packaged: {upsc}"
        upsd = os.path.join(nut.package_folder, "bin", "upsd")
        assert os.path.isfile(upsd), f"upsd was not packaged: {upsd}"
        self.run("sh test_nut.sh", env="conanrun")
