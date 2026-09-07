#!/usr/bin/env python3
"""Conan consumer test for sqlite3 3.53.4."""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class Sqlite3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile and link completed; target execution is deferred")
            return
        if str(self.settings.os) == "Windows":
            self.run("test_sqlite3.exe", env="conanrun")
            return
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run("{} -c './test_sqlite3'".format(bash), env="conanrun")
