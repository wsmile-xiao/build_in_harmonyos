#!/usr/bin/env python3
"""test_package for fdupes — CLI duplicate file finder.

R34: test executes the real fdupes binary via test.sh script.
"""
import os

from conan import ConanFile


class FdupesTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} test.sh", env="conanrun")
