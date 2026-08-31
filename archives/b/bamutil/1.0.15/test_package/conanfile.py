#!/usr/bin/env python3
"""Conan test_package — bamutil command-line tool test."""
import os
from conan import ConanFile
from conan.tools.files import chdir


class BamutilTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Test that bam executable runs and shows help
        self.run("bash test.sh", env="conanrun", cwd=self.source_folder)
