#!/usr/bin/env python3
"""Conan recipe for ninja 1.12.1 — a small build system with a focus on speed.

Ninja is a command-line tool (executable), not a library.
Build system: CMake.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class NinjaConan(ConanFile):
    name = "ninja"
    version = "1.12.1"
    description = "Small build system with a focus on speed"
    license = "Apache-2.0"
    homepage = "https://ninja-build.org/"
    package_type = "application"

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
        # Disable testing to avoid downloading Google Test from GitHub (not accessible on OHOS)
        tc.variables["BUILD_TESTING"] = "OFF"
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
        self.cpp_info.bindirs = ["bin"]
