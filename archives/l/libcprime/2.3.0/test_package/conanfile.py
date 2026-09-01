#!/usr/bin/env python3
"""Conan test_package for libcprime 2.3.0."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibcprimeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        qtbase = self.dependencies["qtbase"]
        qt_prefix = qtbase.package_folder.replace("\\", "/")
        package = self.dependencies["libcprime"]
        pkg_prefix = package.package_folder.replace("\\", "/")

        tc = CMakeToolchain(self)
        tc.cache_variables["LIBCPRIME_INCLUDE_DIR"] = f"{pkg_prefix}/include/cprime"
        tc.cache_variables["LIBCPRIME_LIB_DIR"] = f"{pkg_prefix}/lib"
        tc.cache_variables["CMAKE_PREFIX_PATH"] = f"{qt_prefix}/lib/cmake"
        tc.generate()

        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w", encoding="utf-8") as handle:
            handle.write(
                "\n".join(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH "{qt_prefix}/lib/cmake")',
                        f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_prefix}/lib")',
                        f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_prefix}/include")',
                        f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg_prefix}/lib")',
                        f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg_prefix}/include/cprime")',
                        "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
                    ]
                )
                + "\n"
            )

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            env = Environment()
            for dep in self.dependencies.values():
                if dep.package_folder:
                    libdir = os.path.join(dep.package_folder, "lib")
                    env.append("LD_LIBRARY_PATH", [libdir])
            env.define("QT_QPA_PLATFORM", "offscreen")
            with env.vars(self).apply():
                self.run(os.path.join(self.cpp.build.bindirs[0], "test_libcprime"), env="conanrun")
