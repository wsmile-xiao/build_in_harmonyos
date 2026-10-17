#!/usr/bin/env python3
"""Conan consumer test for the rhai command-line interpreter (rhai-run/rhai-dbg)."""
import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run


class RhaiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["rhai"].package_folder
        script = os.path.join(self.recipe_folder, "test_rhai.py")
        self.run(
            f"{shlex.quote(sys.executable)} {shlex.quote(script)} "
            f"{shlex.quote(package_folder)}",
            env="conanrun",
        )
