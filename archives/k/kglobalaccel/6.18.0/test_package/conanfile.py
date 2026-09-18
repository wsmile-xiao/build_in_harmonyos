#!/usr/bin/env python3
"""Conan test_package for kglobalaccel 6.18.0.

Verifies that KF6GlobalAccel can be found via CMake and that the KGlobalAccel
API is actually callable (R34: real API usage, no empty-shell test).

The KGlobalAccel::self() singleton and static query APIs work without a
running DBus daemon (calls fail gracefully), so the test is headless-safe.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KGlobalAccelTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase-sql-dbus/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        tc.generate()

        qtbase = self.dependencies.get("qtbase-sql-dbus")
        pkg = self.dependencies.get(
            self.tested_reference_str.split("/")[0]
        )
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{pkg.package_folder}/lib/cmake")'
            )
        if qtbase and qtbase.package_folder:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{qtbase.package_folder}/lib/cmake")'
            )
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qtbase.package_folder}/lib")'
            )
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH '
                f'"{qtbase.package_folder}/include")'
            )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH '
                    f'"{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{dep.package_folder}/include")'
                )
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
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                libdir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(libdir):
                    env.append("LD_LIBRARY_PATH", [libdir])
        pkg = self.dependencies.get(
            self.tested_reference_str.split("/")[0]
        )
        if pkg and pkg.package_folder:
            env.append(
                "LD_LIBRARY_PATH",
                [os.path.join(pkg.package_folder, "lib")],
            )
        env.define("QT_QPA_PLATFORM", "offscreen")
        with env.vars(self).apply():
            executable = os.path.join(self.cpp.build.bindirs[0], "test_kglobalaccel")
            self.run(executable, env="conanrun")
