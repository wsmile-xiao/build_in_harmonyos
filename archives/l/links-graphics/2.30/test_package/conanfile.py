#!/usr/bin/env python3
"""Conan test_package — links-graphics 2.30.

Verifies that the links binary is installed and functional.
"""
import os

from conan import ConanFile


class LinksgraphicsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} test.sh", env="conanrun")
