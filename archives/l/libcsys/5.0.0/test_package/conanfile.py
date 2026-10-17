#!/usr/bin/env python3
"""Conan test_package for libcsys 5.0.0.

Consumer-perspective verification (R34): builds a small Qt6 application that
links the installed libcsys and exercises its public csys/*.h API at runtime.
The binary prints an explicit "assertions=N failures=M" summary and exits
non-zero on failure.

libcsys is packaged with cmake_find_mode=none (it installs no CMake config
package), so instead of find_package(csys) the package folder is forwarded to
CMake through toolchain variables, and qtbase-sql-dbus's lib/cmake directory is
injected into CMAKE_PREFIX_PATH by hand (qtbase-sql-dbus is itself
cmake_find_mode=none, so CMakeDeps does not emit conan_cmakedeps_paths.cmake).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibcsysTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.cpp"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Needed for the Qt6Config.cmake prefix path injection in generate().
        self.requires("qtbase-sql-dbus/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        pkg = self.dependencies.get("libcsys")
        if pkg:
            tc.variables["CSYS_INCLUDE_DIR"] = os.path.join(
                pkg.package_folder, "include"
            )
            tc.variables["CSYS_LIBRARY"] = os.path.join(
                pkg.package_folder, "lib", "libcsys.so"
            )
        tc.generate()

        qtbase = self.dependencies.get("qtbase-sql-dbus")
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")'
            )
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
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
        env.append(
            "LD_LIBRARY_PATH",
            [
                os.path.join(p.package_folder, "lib")
                for p in self.dependencies.values()
                if p.package_folder
            ],
        )
        with env.vars(self).apply():
            executable = os.path.join(
                self.cpp.build.bindirs[0], "test_libcsys"
            )
            self.run(executable, env="conanrun")
