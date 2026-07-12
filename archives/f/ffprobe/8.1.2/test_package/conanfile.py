#!/usr/bin/env python3
"""Conan test_package for ffprobe — L1 consumer test.

R34: Test executes the package's binary to verify functionality.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class FfprobeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["ffprobe"]
        ffprobe = os.path.join(pkg.package_folder, "bin", "ffprobe")
        self.run(f'"{ffprobe}" -version', env="conanrun")
