#!/usr/bin/env python3
"""Conan recipe — chipmunk2d 7.0.3 (CMake project).

Chipmunk2D builds a shared (libchipmunk) and static (libchipmunk_static)
library via CMake. Demos require GLFW/Sokol and are disabled (BUILD_DEMOS=OFF).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Chipmunk2DConan(ConanFile):
    name = "chipmunk2d"
    version = "7.0.3"
    description = "Fast, lightweight 2D rigid body physics engine (Chipmunk2D)"
    license = "MIT"
    homepage = "https://chipmunk-physics.net/"
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
        # Demos pull in GLFW/Sokol; not needed for the library package.
        tc.variables["BUILD_DEMOS"] = "OFF"
        tc.variables["INSTALL_DEMOS"] = "OFF"
        tc.variables["BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_STATIC"] = "OFF" if self.options.shared else "ON"
        tc.variables["INSTALL_STATIC"] = "ON" if not self.options.shared else "OFF"
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
        self.cpp_info.libs = ["chipmunk"]
