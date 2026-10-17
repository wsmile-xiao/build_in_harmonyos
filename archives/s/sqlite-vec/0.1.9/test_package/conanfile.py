#!/usr/bin/env python3
"""Conan test_package for sqlite-vec — basic vector search verification."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SqliteVecTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("sqlite3/3.49.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_sqlite_vec"), env="conanrun")
