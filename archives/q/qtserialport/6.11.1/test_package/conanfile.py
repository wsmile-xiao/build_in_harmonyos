#!/usr/bin/env python3
"""Consumer test for qtserialport on HarmonyOS PC."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QtserialportTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase_pkg = self.dependencies["qtbase"].package_folder
        pkg = self.dependencies["qtserialport"].package_folder
        # Qt6Config lives in the qtbase package; Qt6SerialPortConfig lives in
        # the qtserialport package. Qt only searches the additional prefixes
        # listed in QT_ADDITIONAL_PACKAGES_PREFIX_PATH for module configs.
        tc.cache_variables["CMAKE_PREFIX_PATH"] = qtbase_pkg
        tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = pkg
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise ConanInvalidConfiguration(
                    "qtserialport test package has no build bindir"
                )
            executable = os.path.join(bindirs[0], "test_qtserialport")
            self.run(
                executable,
                env="conanrun",
                ignore_errors=False,
            )
