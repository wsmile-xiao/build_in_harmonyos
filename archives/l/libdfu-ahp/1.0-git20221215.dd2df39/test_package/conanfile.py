#!/usr/bin/env python3
"""Consumer test for the public libdfu API."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibdfuAhpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: consumer compile and link completed")
            return

        binary = os.path.join(self.build_folder, "test_libdfu")
        if not os.path.isfile(binary):
            binary = os.path.join(self.build_folder, str(self.settings.build_type), "test_libdfu")
        self.run(f'"{binary}"', env="conanrun")
