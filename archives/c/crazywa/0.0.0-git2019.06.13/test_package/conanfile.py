#!/usr/bin/env python3
"""Conan consumer — CrazyWa 0.0.0-git2019.06.13 (Python unittest)."""
import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class CrazywaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if can_run(self):
            executable = os.path.join(self.dependencies["crazywa"].package_folder, "bin", "crazywa")
            test = os.path.join(self.source_folder, "protocol_test.py")
            self.run("python3 " + shlex.quote(test) + " " + shlex.quote(executable), env="conanrun")
