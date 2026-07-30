#!/usr/bin/env python3
"""Conan test package for CLHEP 2.4.7.1."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class ClhepTestConan(ConanFile):
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
        if can_run(self):
            # CTest must expose CLHEP's component libraries to its child process.
            lib_dir = os.path.join(self.dependencies["clhep"].package_folder, "lib")
            self.run(
                f"LD_LIBRARY_PATH={lib_dir}:$LD_LIBRARY_PATH ctest --output-on-failure",
                cwd=self.build_folder,
            )
        else:
            self.output.info(
                "Skipping CLHEP test package: the target binaries cannot run "
                "on this build machine"
            )
