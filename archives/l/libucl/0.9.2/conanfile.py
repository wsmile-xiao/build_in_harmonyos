#!/usr/bin/env python3
"""Conan recipe — libucl 0.9.2 (CMake)."""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibuclConan(ConanFile):
    name = "libucl"
    version = "0.9.2"
    description = "Universal Configuration Language library"
    license = "BSD-2-Clause"
    homepage = "https://github.com/vstakhov/libucl"
    url = "https://github.com/vstakhov/libucl"

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
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["ENABLE_UTILS"] = False
        tc.variables["ENABLE_LUA"] = False
        tc.variables["ENABLE_LUAJIT"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["ucl"]
        self.cpp_info.system_libs.append("m")
        self.cpp_info.set_property("cmake_file_name", "ucl")
        self.cpp_info.set_property("cmake_target_name", "ucl::ucl")
