#!/usr/bin/env python3
"""Consumer test recipe for the installed platformdirs package."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def configure(self):
        self.settings.rm_safe("os.version")

    def package_id(self):
        self.info.clear()

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise RuntimeError("platformdirs consumer test requires a runnable Python")
        package = self.dependencies["platformdirs"].package_folder
        site = os.path.join(package, "lib", "python3.12", "site-packages")
        test_script = os.path.join(os.path.dirname(__file__), "test_platformdirs.py")
        self.run(f"PYTHONPATH='{site}' python3 '{test_script}'", env="conanrun")
