#!/usr/bin/env python3
"""Test package for otf-atkinson: validates OTF files via test_otf.py."""
import os
from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        font_dir = os.path.join(
            self.dependencies["otf-atkinson"].package_folder,
            "share", "fonts", "OTF",
        )
        test_script = os.path.join(self.source_folder, "test_otf.py")
        self.run(f"python3 {test_script} {font_dir}")
