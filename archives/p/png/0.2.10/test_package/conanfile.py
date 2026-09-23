#!/usr/bin/env python3
"""Conan consumer test for png++ 0.2.10 packaged as png/0.2.10."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class PngTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: png++ compile and link checks passed")
            return

        executable = os.path.join(self.cpp.build.bindir, "test_png")
        if self.settings.os == "OHOS":
            shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f'{shell} -c "{executable}"', env="conanrun")
        else:
            self.run(executable, env="conanrun")
