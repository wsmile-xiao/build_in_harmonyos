#!/usr/bin/env python3
"""Conan test_package for kguiaddons5 5.116.0.

The consumer links against KF5::GuiAddons (libKF5GuiAddons) and the Qt5 GUI
libraries, exercising the real KColorUtils API (blend / mix / contrastRatio)
without requiring a display.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class Kguiaddons5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        qt5 = self.dependencies.get("qt5-qtbase")
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{pkg.package_folder}/lib/cmake")'
            )
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{pkg.package_folder}")'
            )
        if qt5:
            qt_pkg = qt5.package_folder
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        # The generators folder holds the CMakeDeps-generated Qt5 configs
        # (Qt5Config.cmake, Qt5GuiConfig.cmake).
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_kguiaddons5"),
            env="conanrun",
        )
