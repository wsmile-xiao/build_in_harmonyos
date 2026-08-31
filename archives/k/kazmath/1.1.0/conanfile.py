#!/usr/bin/env python3
"""Conan recipe for kazmath 1.1.0."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KazmathConan(ConanFile):
    name = "kazmath"
    version = "1.1.0"
    description = "A C math library aimed at game programming"
    license = "BSD-2-Clause"
    homepage = "https://github.com/Kazade/kazmath"
    url = "https://github.com/Kazade/kazmath"
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
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["KAZMATH_BUILD_TESTS"] = "OFF"
        tc.variables["KAZMATH_BUILD_JNI_WRAPPER"] = "OFF"
        tc.variables["KAZMATH_BUILD_LUA_WRAPPER"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.libs = ["kazmath"]
