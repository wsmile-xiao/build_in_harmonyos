#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test package for click 8.4.2"""

from conan import ConanFile
from conan.tools.build import can_run
import sys


class ClickTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # Run the comprehensive test script (test() executes in test_package/ dir)
            self.run(f'{sys.executable} test_click.py', env="conanrun")