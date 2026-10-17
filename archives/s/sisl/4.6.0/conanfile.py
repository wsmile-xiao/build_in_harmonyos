#!/usr/bin/env python3
"""Conan recipe template — CMake projects.

Usage: Replace Sisl, sisl, 4.6.0, SINTEF Spline Library for curves and surfaces, AGPL-3.0-or-later, https://github.com/SINTEF-Geometry/SISL
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: BUILD_SHARED_LIBS=OFF for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SislConan(ConanFile):
    name = "sisl"
    version = "4.6.0"
    description = "SINTEF Spline Library for curves and surfaces"
    license = "AGPL-3.0-or-later"
    homepage = "https://github.com/SINTEF-Geometry/SISL"
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
        tc.variables["CMAKE_INSTALL_PREFIX"] = "/storage/Users/currentUser/usr/local"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        self.cpp_info.libs = ["sisl"]
