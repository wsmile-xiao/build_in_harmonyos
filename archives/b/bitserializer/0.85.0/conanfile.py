#!/usr/bin/env python3
"""Conan recipe — bitserializer 0.85.0 (CMake, header-only core)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BitserializerConan(ConanFile):
    name = "bitserializer"
    version = "0.85.0"
    description = "C++17 library for serialization to multiple output formats (JSON, XML, YAML, CSV, MsgPack)"
    license = "MIT"
    homepage = "https://github.com/PavelKisliak/BitSerializer"
    url = ""  # CI fills this

    package_type = "header-library"

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
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.variables["BUILD_BENCHMARKS"] = "OFF"
        tc.variables["BUILD_SAMPLES"] = "OFF"
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
        self.cpp_info.set_property("cmake_file_name", "bitserializer")
        self.cpp_info.set_property("cmake_target_name", "BitSerializer::core")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
