#!/usr/bin/env python3
"""Consumer-side test for the furo theme package.

The wheel contents travel inside the recipe (export_sources assets), so the
consumer-side verification runs against the installed package folder: all 85
pinned files byte-identical + theme layout (theme.conf / __init__ / dist-info
METADATA / entry_points) present for Sphinx discovery."""
import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class FuroTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_root = self.dependencies["furo"].package_folder
        script = os.path.join(self.source_folder, "verify_furo.py")
        self.run(
            f'"{sys.executable}" "{script}" '
            f'--package-root "{package_root}"'
        )
        site = os.path.join(package_root, "share", "python", "site-packages")
        for rel in (
            os.path.join("furo", "__init__.py"),
            os.path.join("furo", "theme", "furo", "theme.conf"),
            os.path.join("furo", "theme", "furo", "static", "styles", "furo.css"),
            os.path.join("furo-2024.8.6.dist-info", "METADATA"),
            os.path.join("furo-2024.8.6.dist-info", "entry_points.txt"),
        ):
            assert os.path.isfile(os.path.join(site, rel)), f"{rel} missing under {site}"
        print(f"furo theme layout OK under {site}")
