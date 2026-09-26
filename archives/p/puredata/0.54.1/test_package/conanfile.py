#!/usr/bin/env python3
import os

from conan import ConanFile


class PuredataTestConan(ConanFile):
    """test_package for puredata — CLI executable smoke test."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} test.sh", env="conanrun")
