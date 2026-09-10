#!/usr/bin/env python3
import os

from conan import ConanFile


class ExultTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = os.environ.get("CONFIG_SHELL", "sh")
        self.run(f"{shell} test.sh", env="conanrun")
