#!/usr/bin/env python3
"""Conan test_package for AdapterRemoval 2.3.4."""

import os

from conan import ConanFile


class AdapterRemovalTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        config_shell = os.environ.get("CONFIG_SHELL", "sh")
        self.run(f"{config_shell} test.sh", env="conanrun")
