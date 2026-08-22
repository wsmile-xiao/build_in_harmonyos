#!/usr/bin/env python3
"""Test package for haproxy 3.2.0.

Verifies that the haproxy binary can be executed and reports its version.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class HaproxyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bash = os.environ.get("CONFIG_SHELL", "bash")
            self.run(f"{bash} test.sh", env="conanrun")
