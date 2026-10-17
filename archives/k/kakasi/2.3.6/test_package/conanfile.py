#!/usr/bin/env python3
"""Conan consumer test for package kakasi 2.3.6."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class KakasiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skip runtime consumer test")
            return

        package = self.dependencies["kakasi"]
        binary = os.path.join(package.package_folder, "bin", "kakasi")
        if not os.path.isfile(binary):
            raise AssertionError(f"kakasi binary not found: {binary}")

        python = os.environ.get("PYTHON", "python3")
        script = os.path.join(self.recipe_folder, "test_kakasi.py")
        self.run(f'"{python}" "{script}" "{binary}"', env="conanrun")
