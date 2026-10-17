#!/usr/bin/env python3
"""Conan test_package — aresponses 3.0.0 (Python test).

R34: test must actually import and use the tested package's API.
This test imports aresponses and verifies its ResponsesMockServer class.
"""
import sys
import os

from conan import ConanFile



class AresponsesTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # R34: Must actually import aresponses and use its API
        # Run a Python test that imports the package and exercises its API
        test_script = os.path.join(self.source_folder, "test_aresponses.py")
        self.run(f"{sys.executable} {test_script}", env="conanrun")
