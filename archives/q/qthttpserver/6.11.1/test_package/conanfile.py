#!/usr/bin/env python3
"""Consumer test for the qthttpserver Conan package."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QtHttpServerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Both qtbase-gui and qthttpserver install native Qt CMake files.
        # List every host dependency prefix so find_package(Qt6 COMPONENTS ...)
        # can locate the base modules and HttpServer module together.
        prefixes = [
            dependency.package_folder
            for dependency in self.dependencies.host.values()
        ]
        tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join(prefixes)
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
                    "qthttpserver test package has no build bindir"
                )
            executable = os.path.join(bindirs[0], "test_qthttpserver")
            self.run(executable, env="conanrun", ignore_errors=False)
