#!/usr/bin/env python3
"""test_package conanfile for apertium-mkd-eng.

Validates that the packaged Apertium Macedonian-English linguistic
data files are present, non-empty, and contain the expected content.
"""

import os

from conan import ConanFile


class ApertiumMkdEngTestConan(ConanFile):
    test_type = "explicit"
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["apertium-mkd-eng"]
        test_script = os.path.join(self.source_folder,
                                   "test_apertium.py")
        self.run(f'python3 "{test_script}" "{dep.package_folder}"',
                 env="conanrun")
