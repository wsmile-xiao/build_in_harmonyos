#!/usr/bin/env python3
"""Conan recipe template — CMake projects.

Usage: Replace Libogg, libogg, 1.3.5, Ogg multimedia container library, BSD-3-Clause, https://xiph.org/ogg/
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: BUILD_SHARED_LIBS=OFF for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LiboggConan(ConanFile):
    name = "libogg"
    version = "1.3.5"
    description = "Ogg multimedia container library"
    license = "BSD-3-Clause"
    homepage = "https://xiph.org/ogg/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["ogg"]
