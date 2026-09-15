#!/usr/bin/env python3
"""Consumer test for the packaged clhash C API."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class ClhashTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Skipping test_clhash: target binary cannot run here")
            return
        exe = os.path.join(self.build_folder, "test_clhash")
        if str(self.settings.os) == "Windows":
            exe += ".exe"
        self.run(shlex.quote(exe), env="conanrun")
