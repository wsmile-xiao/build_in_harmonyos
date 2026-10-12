#!/usr/bin/env python3
"""Conan test_package for libaccounts-qt 1.17 (Qt6 / AccountsQt6).

Consumer-side smoke test (L1): links against the packaged library and
exercises the public Accounts:: API, so a stub or empty package cannot pass.

qtbase on ohpcd sets cmake_find_mode=none and ships Qt's own Qt6Config.cmake,
so its conan naming is mapped onto the real Qt6 targets here (actiona /
aethersdr precedent in this repo).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibaccountsQtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        qt_prefix = self.dependencies["qtbase"].package_folder.replace("\\", "/")

        deps = CMakeDeps(self)
        # Map qtbase onto Qt6::Core so the AccountsQt6 interface references a
        # target that exists once Qt's real Qt6Config.cmake is found.
        deps.set_property("qtbase", "cmake_file_name", "Qt6")
        deps.set_property("qtbase", "cmake_target_name", "Qt6::Core")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.cache_variables["Qt6_DIR"] = f"{qt_prefix}/lib/cmake/Qt6"
        tc.cache_variables["CMAKE_PREFIX_PATH"] = f"{qt_prefix}/lib/cmake;{qt_prefix}"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmd = os.path.join(self.cpp.build.bindir, "test_libaccounts_qt")
        self.run(cmd, env="conanrun")
