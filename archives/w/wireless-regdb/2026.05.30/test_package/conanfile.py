#!/usr/bin/env python3
"""Semantic consumer tests for wireless-regdb."""

import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class WirelessRegdbTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def test(self):
        package_root = self.dependencies["wireless-regdb"].package_folder
        script = os.path.join(self.source_folder, "test_wireless_regdb.py")
        command = (
            f'"{sys.executable}" "{script}" '
            f'--package-root "{package_root}"'
        )
        self.run(command, env="conanrun")
