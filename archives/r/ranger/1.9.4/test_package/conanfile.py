#!/usr/bin/env python3
"""Conan test_package for ranger.

Imports the ranger module and verifies the version,
then checks that rifle entry-point is accessible.
"""
from conan import ConanFile


class RangerTestConan(ConanFile):
    """test_package for ranger application package."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("python3 test_ranger.py", env="conanrun")
