#!/usr/bin/env python3
"""Consumer test for the public vectorscan block-scanning API."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class VectorscanTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_C_STANDARD"] = 11
        tc.variables["CMAKE_C_STANDARD_REQUIRED"] = True
        tc.variables["CMAKE_C_EXTENSIONS"] = False
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning(
                "test_package runtime checks were skipped because the target "
                "executable cannot run in the current cross-compilation environment"
            )
            return

        executable = os.path.join(self.build_folder, "test_vectorscan")
        self.run(f'"{executable}"', env="conanrun")
