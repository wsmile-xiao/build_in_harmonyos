#!/usr/bin/env python3
"""Exercise the packaged ITK core module."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class ItkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self, build_folder="b")

    def generate(self):
        tc = CMakeToolchain(self)
        itk_dir = os.path.join(
            self.dependencies["itk"].package_folder, "lib", "cmake", "ITK-5.4"
        )
        tc.cache_variables["ITK_DIR"] = itk_dir.replace("\\", "/")
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        if not can_run(self):
            return
        executable = os.path.join(self.cpp.build.bindirs[0], "test_itk_consumer")
        self.run(executable, env="conanrun")
