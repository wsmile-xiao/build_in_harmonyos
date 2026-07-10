#!/usr/bin/env python3
"""Conan recipe — physfs 3.2.0 (CMake project).

PhysicsFS: filesystem abstraction library for game archive access (ZIP, 7z, etc.)
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PhysfsConan(ConanFile):
    name = "physfs"
    version = "3.2.0"
    description = "Filesystem abstraction library for game archive access (ZIP, 7z, etc.)"
    license = "Zlib"
    homepage = "https://icculus.org/physfs/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

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
        # CMake 4.x removed compatibility with < 3.5; physfs requires 3.0.0
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["physfs"]
