#!/usr/bin/env python3
"""Conan test_package — jq 1.7.1

Runs test.sh which exercises jq's JSON processing and regex (oniguruma) support.
"""
import os

from conan import ConanFile


class JqTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f"sh {script}", env="conanrun")
