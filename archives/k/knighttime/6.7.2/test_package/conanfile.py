#!/usr/bin/env python3
"""Conan test_package for knighttime 6.7.2.

Verifies that the KNightTime library is discoverable via CMake
(find_package(KNightTime) + KNightTime link) and that the core public API
computes real dark-light schedules — both the fixed-times forecast and the
sun-driven forecast (which exercises the KHolidays::SunEvents dependency
end to end), plus transition navigation and state serialization
(R34: real API usage).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KnighttimeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtpositioning/6.11.1")
        self.requires("kholidays/6.28.0")
        self.requires("kconfig/6.26.0")
        self.requires("kcoreaddons/6.26.0")
        self.requires("kdbusaddons/6.18.0")
        self.requires("ki18n/6.26.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.blocks.remove("cppstd")
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.generate()

        lines = [
            'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
        ]
        for dep in self.dependencies.host.values():
            if dep and dep.package_folder:
                dep_cmake = os.path.join(dep.package_folder, "lib", "cmake")
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{dep_cmake}")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH '
                    f'"{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{dep.package_folder}/include")'
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
        test_env = Environment()
        for d in self.dependencies.values():
            if d and d.package_folder:
                test_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(d.package_folder, "lib")
                )
        test_env.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.build_folder)
        )
        if self.settings.os == "OHOS":
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        with test_env.vars(self).apply():
            self.run(
                os.path.join(self.build_folder, "test_knighttime"),
                env="conanrun",
            )
