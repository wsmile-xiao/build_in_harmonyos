#!/usr/bin/env python3
"""Conan test_package for ctrl-c 1.0.0 (Conan L1 consumer test).

CI runs this through `conan create`; PF3/L0d require test() to call self.run.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CtrlcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            path = os.path.join(self.build_folder, "bin", "test_ctrl_c")
            self.run('"{}"'.format(path), env="conanrun")
