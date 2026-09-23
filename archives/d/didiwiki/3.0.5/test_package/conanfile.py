#!/usr/bin/env python3
"""test_package for didiwiki executable (ciwiki)."""
import os

from conan import ConanFile


class DidiwikiTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the ciwiki binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
