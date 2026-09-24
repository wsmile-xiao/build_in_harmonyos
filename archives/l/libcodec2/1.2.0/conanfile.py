#!/usr/bin/env python3
"""Conan recipe — libcodec2 1.2.0

Codec2: Next-Generation Digital Voice for Two-Way Radio.
CMake-based build with no external dependencies (standalone).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Codec2Conan(ConanFile):
    name = "libcodec2"
    version = "1.2.0"
    description = "Next-Generation Digital Voice for Two-Way Radio"
    license = "LGPL-2.1"
    homepage = "https://www.rowetel.com/codec2.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["UNITTEST"] = "OFF"
        tc.variables["LPCNET"] = "OFF"
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
        self.cpp_info.libs = ["codec2"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "codec2")
        self.cpp_info.set_property("cmake_target_name", "codec2::codec2")
        self.cpp_info.set_property("pkg_config_name", "codec2")
