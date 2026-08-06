#!/usr/bin/env python3
"""Conan recipe for CRoaring 4.6.1 — C/C++ Roaring Bitmap library.

Upstream: https://github.com/RoaringBitmap/CRoaring
License:  Apache-2.0
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CroaringConan(ConanFile):
    name = "croaring"
    version = "4.6.1"
    description = "C/C++ Roaring Bitmap high-performance bitmap library"
    license = "Apache-2.0"
    homepage = "https://roaringbitmap.org/"
    url = "https://github.com/RoaringBitmap/CRoaring"

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
        tc.variables["ENABLE_ROARING_TESTS"] = "OFF"
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
        self.cpp_info.libs = ["roaring"]
        self.cpp_info.set_property("cmake_file_name", "croaring")
        self.cpp_info.set_property("cmake_target_name", "croaring::croaring")
