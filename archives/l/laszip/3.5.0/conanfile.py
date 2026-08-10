#!/usr/bin/env python3
"""Conan recipe — laszip 3.5.0 (CMake)"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class LaszipConan(ConanFile):
    name = "laszip"
    version = "3.5.0"
    description = "Lossless compression for LiDAR data (LAS format)"
    licenses = "LGPL-2.1"
    homepage = "https://github.com/LASzip/LASzip"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": True,
    }

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
        if not self.options.shared:
            tc.variables["LASZIP_BUILD_STATIC"] = True
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
        self.cpp_info.libs = ["laszip", "laszip_api"]
        # laszip_api.h internally includes <laszip_common.h> without the
        # laszip/ prefix, so include/laszip must be in the search path
        self.cpp_info.includedirs = ["include", "include/laszip"]
