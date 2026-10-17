#!/usr/bin/env python3
"""Conan test package for bpytop 1.0.68."""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class BpytopTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        package_folder = dep.package_folder
        exe = os.path.join(package_folder, "bin", "bpytop")
        themes_dir = os.path.join(package_folder, "share", "bpytop", "themes")

        if not os.path.exists(exe):
            raise AssertionError(f"Missing bpytop executable: {exe}")
        if not os.path.isdir(themes_dir):
            raise AssertionError(f"Missing bpytop themes directory: {themes_dir}")

        if not can_run(self):
            return

        test_script = os.path.join(self.source_folder, "test_bpytop_version.py")
        self.run(
            f'"{sys.executable}" "{test_script}" "{exe}" "{sys.executable}"',
            env="conanrun",
        )
