#!/usr/bin/env python3
"""Consumer test for Qt Remote Objects 6.11.1."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QtRemoteObjectsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase = self.dependencies["qtbase"].package_folder
        qtremoteobjects = self.dependencies["qtremoteobjects"].package_folder
        tc.variables["Qt6_DIR"] = os.path.join(qtbase, "lib", "cmake", "Qt6")
        tc.variables["Qt6RemoteObjects_DIR"] = os.path.join(
            qtremoteobjects, "lib", "cmake", "Qt6RemoteObjects"
        )
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run("./test_package", env="conanrun")
