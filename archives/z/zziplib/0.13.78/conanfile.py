#!/usr/bin/env python3
"""Conan recipe for zziplib 0.13.78 — CMake build system.

zziplib is a lightweight library to easily extract data from zip files.
Build: CMake with BUILD_SHARED_LIBS=OFF (R26 system-name library constraint).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ZziplibConan(ConanFile):
    name = "zziplib"
    version = "0.13.78"
    description = "Lightweight library for reading zip files."
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/gdraheim/zziplib"
    url = "https://github.com/gdraheim/zziplib"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.variables["ZZIPMMAPPED"] = "OFF"
        tc.variables["ZZIPFSEEKO"] = "OFF"
        tc.variables["ZZIPWRAP"] = "OFF"
        tc.variables["ZZIPSDL"] = "OFF"
        tc.variables["ZZIPBINS"] = "OFF"
        tc.variables["ZZIPTEST"] = "OFF"
        tc.variables["ZZIPDOCS"] = "OFF"
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
        self.cpp_info.libs = ["zzip"]
        self.cpp_info.set_property("cmake_file_name", "zziplib")
        self.cpp_info.set_property("cmake_target_name", "zziplib::zziplib")
        self.cpp_info.set_property("pkg_config_name", "zziplib")