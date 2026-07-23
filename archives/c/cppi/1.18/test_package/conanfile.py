#!/usr/bin/env python3
"""Conan test_package for cppi 1.18 — verify CLI tool works."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class CppiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        bash = os.environ.get("CONFIG_SHELL", "sh")
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run("{} {}".format(bash, test_script), env="conanrun")
