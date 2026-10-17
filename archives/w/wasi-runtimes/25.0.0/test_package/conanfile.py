#!/usr/bin/env python3
"""Conan test_package for wasi-runtimes 25.0.0."""
import os
import shlex
import sys

from conan import ConanFile


class WasiRuntimesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        root = next(iter(self.dependencies.values())).package_folder
        script = os.path.join(self.recipe_folder, "check_wasi_assets.py")
        self.run(" ".join(shlex.quote(arg) for arg in (sys.executable, script, root)))
