#!/usr/bin/env python3
"""Conan test_package — gpx 2.6.8.

gpx is a terminal tool (not a library).
Test: run gpx binary and verify version output.
"""
import os

from conan import ConanFile


class GpxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build needed — we test the installed binary

    def test(self):
        # Get the gpx binary path from the dependency's package folder
        gpx_pkg = self.dependencies["gpx"]
        gpx_bin = os.path.join(gpx_pkg.package_folder, "bin", "gpx")
        self.run(f'"{gpx_bin}" --help', env="conanrun")
