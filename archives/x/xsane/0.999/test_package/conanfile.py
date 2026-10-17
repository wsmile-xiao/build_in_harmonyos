#!/usr/bin/env python3
"""Conan test package for xsane 0.999."""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class XsaneTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        pkg = self.dependencies["xsane"].package_folder
        xsane_bin = os.path.join(pkg, "bin", "xsane")
        if not os.path.isfile(xsane_bin):
            raise ConanException(f"xsane binary missing: {xsane_bin}")

        smoke = os.path.join(os.path.dirname(__file__), "test_xsane.py")
        if not can_run(self):
            self.output.info("Runnable smoke skipped on this target")
            return

        self.run(f'"{sys.executable}" "{smoke}" "{xsane_bin}"', env="conanrun")
