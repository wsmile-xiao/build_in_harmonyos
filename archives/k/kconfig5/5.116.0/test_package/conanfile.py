#!/usr/bin/env python3
"""Conan test_package for kconfig5 5.116.0.

Verifies that the KF5ConfigCore library can be found via CMake and that
the KConfig/KConfigGroup API is callable (R34: real API usage).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class Kconfig5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        qtbase = self.dependencies.get("qt5-qtbase")
        pkg = self.dependencies.get(
            self.tested_reference_str.split("/")[0]
        )
        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
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
        env = Environment()
        env.append("LD_LIBRARY_PATH", [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ])
        # KConfig writes under XDG_CONFIG_HOME; point it at a writable dir
        # (the OHOS sandbox /data/storage/el2 is not writable from tests).
        writable = os.path.join(self.build_folder, "cfg")
        os.makedirs(writable, exist_ok=True)
        env.define("XDG_CONFIG_HOME", writable)
        env.define("XDG_CACHE_HOME", writable)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kconfig5"),
                env="conanrun",
            )
