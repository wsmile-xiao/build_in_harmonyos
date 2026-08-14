#!/usr/bin/env python3
"""Conan test_package for GNU ELPA org 9.8.8."""

import os
import shlex

from conan import ConanFile


class OrgTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.recipe_folder, "test_org.sh")
        self.run(f"sh {shlex.quote(script)}", env="conanrun")
