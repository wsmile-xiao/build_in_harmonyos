#!/usr/bin/env python3
"""Conan consumer test for url-normalize 2.2.1."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class UrlNormalizeTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def test(self):
        if not can_run(self):
            return

        test_script = os.path.join(
            self.source_folder,
            "test_url_normalize.py",
        )
        self.run(f'"{sys.executable}" "{test_script}"', env="conanrun")
