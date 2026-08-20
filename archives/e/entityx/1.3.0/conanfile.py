#!/usr/bin/env python3
"""Conan recipe for entityx 1.3.0 — CMake projects.

entityx is a C++11 Entity-Component-System library.
Build system: CMake (cmake_minimum_required 3.1).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class EntityxConan(ConanFile):
    name = "entityx"
    version = "1.3.0"
    description = "Entity-Component System (ECS) library for C++11"
    license = "MIT"
    homepage = "https://github.com/alecthomas/entityx"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["ENTITYX_BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["ENTITYX_BUILD_TESTING"] = "OFF"
        tc.variables["ENTITYX_ENABLE_EXAMPLE_TARGET"] = "OFF"
        # CMake 4.x compat: cmake_minimum_required bumped via patch
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
        self.cpp_info.libs = ["entityx"]
