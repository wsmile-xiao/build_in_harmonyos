#!/usr/bin/env python3
"""Conan test_package for kdegraphics-mobipocket 26.04.1.

Tests that the QMobipocket6 library can be found via CMake and that
its API (Mobipocket::Document) is callable.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KdegraphicsMobipocketTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Explicitly require qtbase so its package folder is available
        # for path setup in generate().
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        # qtbase uses cmake_find_mode=none, so CMakeDeps doesn't add its
        # lib/cmake to CMAKE_PREFIX_PATH. Without this, the installed
        # QMobipocket6Config.cmake can't find Qt6Core via find_dependency.
        # Also add the tested package's lib/cmake so find_package(QMobipocket6)
        # finds the installed config.
        qtbase = self.dependencies.get("qtbase")
        pkg = self.dependencies.get(
            self.tested_reference_str.split("/")[0]
        )
        lines = [
            'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
        ]
        if pkg:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{pkg.package_folder}/lib/cmake")'
            )
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{qt_pkg}/lib/cmake")'
            )
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")'
            )
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")'
            )
        lines.append(
            f'list(PREPEND CMAKE_PREFIX_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        lines.append(
            f'list(PREPEND CMAKE_MODULE_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
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
        # Qt6 may require the offscreen platform plugin for headless tests
        env = Environment()
        env.define("QT_QPA_PLATFORM", "offscreen")
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            # Run the test binary directly (R34: test must exercise the package)
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_mobipocket"),
                env="conanrun",
            )
