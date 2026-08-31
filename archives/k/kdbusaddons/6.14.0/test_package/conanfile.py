#!/usr/bin/env python3
"""Conan test_package for kdbusaddons 6.14.0.

Verifies that the KF6DBusAddons library can be found via CMake and that the
KDEDModule API is callable (R34: real API usage — construct a KDEDModule,
set/read the module name and exercise the static moduleForMessage() parser).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KdbusaddonsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Explicitly require qtbase-sql-dbus so its package folder is
        # available for path setup in generate().
        self.requires("qtbase-sql-dbus/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        # qtbase-sql-dbus uses cmake_find_mode=none, so CMakeDeps doesn't add
        # its lib/cmake to CMAKE_PREFIX_PATH. Without this, the installed
        # KF6DBusAddonsConfig.cmake can't find Qt6DBus via find_dependency().
        qtbase = self.dependencies.get("qtbase-sql-dbus")
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
        env = Environment()
        env.append("LD_LIBRARY_PATH", [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ])
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            # Run the test binary directly (R34: test must exercise the package)
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kdbusaddons"),
                env="conanrun",
            )
