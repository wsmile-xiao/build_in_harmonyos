#!/usr/bin/env python3
"""Conan test_package — poster 20050907.

Runs the packaged poster binary through its stdin->stdout PostScript
pipeline (R34 — executes the package's binary):
1. default run       — A4 1:1 pass-through scaling
2. -p2x2A4 tile run  — poster magnified and tiled across 4 sheets
3. -mA2 media switch — output media changed from A4 to A2
4. -s2 scale run     — linear magnification 2 on A4 (4x2 tiles)
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class PosterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["poster"]
        binary = os.path.join(dep.package_folder, "bin", "poster")
        script = os.path.join(self.source_folder, "test_poster.py")
        self.run(f'python3 "{script}" "{binary}"', env="conanrun")
