#!/usr/bin/env python3
"""Conan recipe for SQLiteCpp 3.3.3 — CMake project.

SQLiteCpp is a C++ wrapper around the SQLite3 C library. It builds an
internal sqlite3 from source (SQLITECPP_INTERNAL_SQLITE=ON, the upstream
default), so there is no external dependency to provision.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SqlitecppConan(ConanFile):
    name = "sqlitecpp"
    version = "3.3.3"
    description = "SQLiteCpp is a smart and easy to use C++ SQLite3 wrapper"
    license = "MIT"
    homepage = "https://github.com/SRombauts/SQLiteCpp"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # sqlite3 is compiled from source inside the upstream tree, no external deps.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Build the bundled sqlite3 (upstream default), skip cpplint/doxygen
        tc.variables["SQLITECPP_INTERNAL_SQLITE"] = "ON"
        tc.variables["SQLITECPP_RUN_CPPLINT"] = "OFF"
        tc.variables["SQLITECPP_RUN_DOXYGEN"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["SQLiteCpp", "sqlite3"]
