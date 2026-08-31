#!/usr/bin/env python3
"""Conan test_package for json5 — runs the R34 consumer check.

L1 official test: runs a Python script that imports the packaged json5 and
parses a JSON5 string (comment + trailing comma). R34 real API usage, not
just file presence.
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["json5"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_json5.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}"',
                     env="conanrun")
