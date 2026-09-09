#!/usr/bin/env python3
"""Conan test_package for blimps 3.9."""
import os

from conan import ConanFile


class BlimpsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test_blimps.sh")
        self.run(f'"{bash}" "{script}"', env="conanrun")
