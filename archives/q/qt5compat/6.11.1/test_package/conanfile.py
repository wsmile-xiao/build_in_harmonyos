#!/usr/bin/env python3
"""Conan test_package for Qt5Compat 6.11.1."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Qt5CompatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMAKE_PREFIX_PATH must include both qtbase (for Qt6Config.cmake)
        # and qt5compat (for Qt6Core5CompatConfig.cmake)
        qtbase = self.dependencies["qt5compat"].dependencies["qtbase"].package_folder
        q5c = self.dependencies["qt5compat"].package_folder
        tc.variables["CMAKE_PREFIX_PATH"] = q5c
        # Also set Qt6_DIR to qtbase for the Qt6 module system
        tc.variables["Qt6_DIR"] = os.path.join(qtbase, "lib", "cmake", "Qt6")
        # Explicitly set Qt6Core5Compat_DIR so find_package(Qt6 COMPONENTS Core5Compat)
        # can find the component
        q5c_cmake = os.path.join(q5c, "lib", "cmake", "Qt6Core5Compat")
        if os.path.isdir(q5c_cmake):
            tc.variables["Qt6Core5Compat_DIR"] = q5c_cmake
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary directly (required by CI L0d check)
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_qt5compat"),
            env="conanrun",
        )