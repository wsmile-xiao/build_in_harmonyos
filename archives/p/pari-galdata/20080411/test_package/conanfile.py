#!/usr/bin/env python3
"""Consumer-side test for the pari-galdata data package (R34 data-package
exemption: no API to call — the test verifies that the packaged data is
complete, byte-identical to the official release, and structurally
sound)."""

import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class PariGaldataTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def test(self):
        package_root = self.dependencies["pari-galdata"].package_folder
        script = os.path.join(
            self.source_folder,
            "test_pari_galdata.py",
        )
        command = (
            f'"{sys.executable}" "{script}" '
            f'--package-root "{package_root}"'
        )
        self.run(command, env="conanrun")
