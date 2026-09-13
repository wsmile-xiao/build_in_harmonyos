#!/usr/bin/env python3
"""Test package for cloudpickle — real runtime smoke on HarmonyOS PC.

R34: actually imports the installed cloudpickle package and round-trips
a lambda through dump/load.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class CloudpickleTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    package_type = "python-require"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["cloudpickle"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        if not os.path.isdir(site):
            raise ConanException(f"no site-packages: {site}")
        script = os.path.join(self.recipe_folder, "test_cloudpickle.py")
        self.run(f'PYTHONPATH="{site}" python3 "{script}"')