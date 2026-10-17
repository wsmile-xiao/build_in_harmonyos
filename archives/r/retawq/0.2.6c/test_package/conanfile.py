#!/usr/bin/env python3
import os

from conan import ConanFile


class RetawqTestConan(ConanFile):
    """test_package for retawq — CLI web browser for text terminals."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} test.sh", env="conanrun")
