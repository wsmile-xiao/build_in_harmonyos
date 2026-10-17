#!/usr/bin/env python3
"""Conan consumer test for words 2.1's installed data files."""

import os
import sys

from conan import ConanFile


class WordsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["words"].package_folder
        script = os.path.join(os.path.dirname(__file__), "test_words.py")
        command = f'"{sys.executable}" "{script}" "{package_folder}"'
        self.run(command, env="conanrun")
