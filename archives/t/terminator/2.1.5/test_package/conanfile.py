#!/usr/bin/env python3
"""Conan test_package for terminator 2.1.5 — Python import smoke test.

Verifies that the terminatorlib Python module can be imported after
``conan create``.
"""
import os
import sys

from conan import ConanFile


class TerminatorTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Smoke test: run test_terminator.py which imports terminatorlib and checks version
        test_script = os.path.join(self.recipe_folder, "test_terminator.py")
        self.run(f'"{sys.executable}" "{test_script}"', env="conanrun")
