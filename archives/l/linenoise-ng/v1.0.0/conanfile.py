#!/usr/bin/env python3
"""Conan recipe template — CMake projects.

Usage: Replace Linenoiseng, linenoise-ng, v1.0.0, linenoise-ng v1.0.0, MIT, 
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: BUILD_SHARED_LIBS=OFF for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LinenoisengConan(ConanFile):
    name = "linenoise-ng"
    version = "v1.0.0"
    description = "linenoise-ng — A minimal, zero-config, BSD-licensed readline replacement (C++)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/arangodb/linenoise-ng"
    url = "https://github.com/arangodb/linenoise-ng"

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
        # Add project-specific CMake variables here:
        # tc.variables["ENABLE_FOO"] = "ON"
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
        # Upstream CMake target is named "linenoise" (liblinenoise.a)
        self.cpp_info.libs = ["linenoise"]
        # Static archive holds C++ objects behind a C API (E247): a pure C
        # consumer must link the C++ runtime too.
        self.cpp_info.system_libs = ["c++"]
