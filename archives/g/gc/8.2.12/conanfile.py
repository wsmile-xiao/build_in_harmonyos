#!/usr/bin/env python3
"""Conan recipe for bdwgc (Boehm-Demers-Weiser GC) 8.2.12.

Build system: CMake (autotools has HMDFS permission issues on OHOS).
Patches: 2 OHOS platform patches (pthread_cancel compatibility).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class GcConan(ConanFile):
    name = "gc"
    version = "8.2.12"
    description = "Boehm-Demers-Weiser garbage collector for C/C++"
    license = "MIT"
    homepage = "https://github.com/ivmai/bdwgc"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external dependencies — uses compiler built-in atomics
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["build_cord"] = "ON"
        tc.variables["without_libatomic_ops"] = "OFF"
        tc.variables["enable_docs"] = "OFF"
        tc.variables["build_tests"] = "OFF"
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
        self.cpp_info.libs = ["gc", "cord"]
