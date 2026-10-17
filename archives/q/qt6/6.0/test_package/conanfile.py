#!/usr/bin/env python3
"""Installed-package consumer for Qt 6.0 Core, Network, Gui, Widgets and Xml."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Qt6TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        package_prefix = self.dependencies["qt6"].package_folder
        tc.cache_variables["CMAKE_PREFIX_PATH"] = package_prefix
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
                    "qt6 test package has no build bindir"
                )
            executable = os.path.join(bindirs[0], "test_qt6")
            self.run(executable, env="conanrun", ignore_errors=False)
