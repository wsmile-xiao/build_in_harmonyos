#!/usr/bin/env python3
"""Consumer test package for Cassiopee 1.0.9 (CMake)."""

from os.path import join

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import VirtualRunEnv


class CassiopeeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run(
                join(self.cpp.build.bindirs[0], "cassiopee_consumer"),
                cwd=self.build_folder,
                env="conanrun",
            )
