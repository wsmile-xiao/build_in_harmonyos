#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test package for typer 0.27.0"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class TyperTestConan(ConanFile):
    # Pure-Python test package: no compiler/build_type needed.
    settings = "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # test() runs in self.build_folder; test_typer.py lives in the
            # source folder alongside this conanfile.py. Use an absolute path.
            test_script = os.path.join(self.source_folder, "test_typer.py")
            self.run(f'python3 "{test_script}"', env=["conanrun"])