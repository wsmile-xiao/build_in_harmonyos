#!/usr/bin/env python3
"""Consumer smoke test for the installed jGrowl distribution assets."""
import os
import sys

from conan import ConanFile


class JgrowlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["jgrowl"].package_folder
        upstream_test = os.path.join(self.source_folder, "verify_upstream_jshint.py")
        self.run(
            f'"{sys.executable}" "{upstream_test}"',
            env="conanrun",
        )
        script = os.path.join(self.source_folder, "verify_assets.py")
        self.run(
            f'"{sys.executable}" "{script}" "{package}"',
            env="conanrun",
        )
