#!/usr/bin/env python3
"""Conan test_package for html5lib — runs the R34 consumer check.

L1 official test: runs a Python script that loads the packaged
html5lib and parses a real HTML document, asserting the parsed tree.
R34 real API usage, not just file presence.
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
            pkg = self.dependencies["html5lib"].package_folder
            # html5lib 运行时依赖 six + webencodings——test 需同时注入其 site-packages
            six_pkg = self.dependencies["six"].package_folder
            we_pkg = self.dependencies["webencodings"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_html5lib.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}" "{six_pkg}" "{we_pkg}"',
                     env="conanrun")
