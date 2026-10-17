#!/usr/bin/env python3
import os

from conan import ConanFile


class AamathTestConan(ConanFile):
    """test_package for aamath — CLI tool that renders math as ASCII art."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} test.sh", env="conanrun")
