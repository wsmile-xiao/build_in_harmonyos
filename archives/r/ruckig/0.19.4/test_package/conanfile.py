#!/usr/bin/env python3
"""Conan test package - Ruckig 0.19.4 consumer and device test."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class RuckigTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    exports_sources = "CMakeLists.txt", "test_main.cpp", "run_test.sh"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        suffix = ".exe" if self.settings.os == "Windows" else ""
        binary = os.path.join(self.cpp.build.bindirs[0], "ruckig_test" + suffix)
        if self.settings.os == "Windows":
            self.run(f'"{binary}"', env="conanrun")
            return
        runner = os.path.join(self.source_folder, "run_test.sh")
        self.run(f'bash "{runner}" "{binary}"', env="conanrun")
