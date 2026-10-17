#!/usr/bin/env python3
"""Conan recipe template — CMake projects.

Usage: Replace Pegtl, pegtl, 4.0.0, Parsing Expression Grammar Template Library - Header-only C++ parser library, MIT, https://github.com/taocpp/pegtl
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: BUILD_SHARED_LIBS=OFF for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PegtlConan(ConanFile):
    name = "pegtl"
    version = "4.0.0"
    description = "Parsing Expression Grammar Template Library - Header-only C++ parser library"
    license = "MIT"
    homepage = "https://github.com/taocpp/pegtl"
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
        # Add project-specific CMake variables here:
        # tc.variables["ENABLE_FOO"] = "ON"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.variables["PEGTL_BUILD_TESTS"] = "OFF"
        tc.variables["PEGTL_BUILD_EXAMPLES"] = "OFF"
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
        # pegtl is a header-only library: no libraries to link.
        self.cpp_info.set_property("cmake_file_name", "pegtl")
        self.cpp_info.set_property("cmake_target_name", "pegtl::pegtl")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = []
