#!/usr/bin/env python3
"""Conan test_package — vsearch 2.30.5 (command-line tool)."""
from conan import ConanFile
from conan.tools.build import can_run


class VsearchTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            self.run("sh test.sh", env="conanrun")
