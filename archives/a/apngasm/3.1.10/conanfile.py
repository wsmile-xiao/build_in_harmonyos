#!/usr/bin/env python3
"""Conan recipe — apngasm 3.1.10 (cmake)

APNG assembler library: create Animated PNG files from a sequence of images.
Build system: CMake (C++20)
Dependencies: libpng, boost (program_options, regex, system), zlib
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class ApngasmConan(ConanFile):
    name = "apngasm"
    version = "3.1.10"
    description = "APNG assembler - create Animated PNG files from sequence of images"
    license = "Zlib"
    homepage = "https://github.com/apngasm/apngasm"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpng/1.6.39")
        self.requires("boost/1.84.0")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        cmake_deps = CMakeDeps(self)
        cmake_deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
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
        self.cpp_info.libs = ["apngasm"]
        self.cpp_info.requires = ["libpng::libpng", "zlib::zlib", "boost::boost"]
        self.cpp_info.bindirs = ["bin"]
