#!/usr/bin/env python3
"""Consumer-side test for the pari-seadata-big data package (R34 data-package
exemption: no API to call — the test verifies that the packaged data is
complete, byte-identical to the official release, and decodable)."""

import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class PariSeadataBigTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def test(self):
        package_root = self.dependencies["pari-seadata-big"].package_folder
        script = os.path.join(
            self.source_folder,
            "verify_seadata_big.py",
        )
        self.run(
            f'"{sys.executable}" "{script}" '
            f'--package-root "{package_root}"',
            env="conanrun",
        )
