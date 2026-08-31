#!/usr/bin/env python3
"""Consumer test for qtscxml (Qt6Scxml + Qt6StateMachine) on HarmonyOS PC."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QtscxmlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # qtbase is a cmake_find_mode "none" dependency: its Qt6Config.cmake
        # lives in lib/cmake/Qt6, and the module configs are found via the
        # *DIR cache variables rather than CMakeDeps.
        qtbase_prefix = self.dependencies["qtbase"].package_folder
        qtscxml_prefix = self.dependencies["qtscxml"].package_folder
        tc.cache_variables["Qt6_DIR"] = os.path.join(
            qtbase_prefix, "lib", "cmake", "Qt6"
        )
        tc.cache_variables["Qt6Scxml_DIR"] = os.path.join(
            qtscxml_prefix, "lib", "cmake", "Qt6Scxml"
        )
        tc.cache_variables["Qt6StateMachine_DIR"] = os.path.join(
            qtscxml_prefix, "lib", "cmake", "Qt6StateMachine"
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
                    "qtscxml test package has no build bindir"
                )
            executable = os.path.join(bindirs[0], "test_qtscxml")
            self.run(
                executable,
                env="conanrun",
                ignore_errors=False,
            )
