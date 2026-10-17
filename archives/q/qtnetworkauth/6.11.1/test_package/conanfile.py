#!/usr/bin/env python3
"""Consumer test for qtnetworkauth without a display server."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QtnetworkauthTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # qtbase ships relocatable Qt6Config.cmake; point the Qt6 component
        # dirs at the installed configs directly (CMakeToolchain only prepends
        # builddirs, not the Qt6*_DIR variables the configs resolve through).
        qtbase_prefix = self.dependencies["qtbase"].package_folder
        qtnetworkauth_prefix = self.dependencies["qtnetworkauth"].package_folder
        tc.cache_variables["Qt6_DIR"] = os.path.join(
            qtbase_prefix, "lib", "cmake", "Qt6"
        )
        tc.cache_variables["Qt6NetworkAuth_DIR"] = os.path.join(
            qtnetworkauth_prefix, "lib", "cmake", "Qt6NetworkAuth"
        )
        # Platform/HarmonyOS.cmake ships with qtbase's install.
        qtbase_platforms = os.path.join(
            qtbase_prefix, "lib", "cmake", "Qt6", "platforms"
        )
        tc.cache_variables["CMAKE_MODULE_PATH"] = qtbase_platforms
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
                    "qtnetworkauth test package has no build bindir"
                )
            executable = os.path.join(bindirs[0], "test_qtnetworkauth")
            self.run(
                executable,
                env="conanrun",
                ignore_errors=False,
            )
