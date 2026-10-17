#!/usr/bin/env python3
"""Consumer test for zycore-c/1.5.1."""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class ZycoreCTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
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
        if cross_building(self):
            self.output.info("cross-building: consumer compiled and linked")
            return
        executable = os.path.join(self.cpp.build.bindirs[0], "test_zycore_c")
        self.run(executable, env="conanrun")
        ohos_executable = os.path.join(self.cpp.build.bindirs[0], "test_zycore_ohos")
        self.run(ohos_executable, env="conanrun")