#!/usr/bin/env python3
"""Conan test_package for spawn-fcgi 1.6.6 — Conan L1 official test.

Verifies that the spawn-fcgi binary is functional by running
`spawn-fcgi -v` and checking the version output.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class SpawnFcgiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        bin_path = os.path.join(self.dependencies["spawn-fcgi"].package_folder, "bin", "spawn-fcgi")
        self.run(f'"{bin_path}" -v', env="conanrun")
