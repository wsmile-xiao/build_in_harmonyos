#!/usr/bin/env python3
"""Consumer test for qtsvg without a display server."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QtsvgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMakeToolchain only prepends dependency builddirs to CMAKE_PREFIX_PATH;
        # the Qt6 component configs are found via the *DIR cache variables, so
        # point Qt6_DIR at qtbase's config and Qt6Svg_DIR at qtsvg's config.
        qtbase_prefix = self.dependencies["qtbase"].package_folder
        qtsvg_prefix = self.dependencies["qtsvg"].package_folder
        tc.cache_variables["Qt6_DIR"] = os.path.join(
            qtbase_prefix, "lib", "cmake", "Qt6"
        )
        tc.cache_variables["Qt6Svg_DIR"] = os.path.join(
            qtsvg_prefix, "lib", "cmake", "Qt6Svg"
        )
        tc.cache_variables["Qt6SvgWidgets_DIR"] = os.path.join(
            qtsvg_prefix, "lib", "cmake", "Qt6SvgWidgets"
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
                    "qtsvg test package has no build bindir"
                )
            executable = os.path.join(bindirs[0], "test_qtsvg")
            self.run(
                executable,
                env="conanrun",
                ignore_errors=False,
            )
