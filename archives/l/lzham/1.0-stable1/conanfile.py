#!/usr/bin/env python3
"""Conan recipe — lzham (CMake project)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LzhamConan(ConanFile):
    name = "lzham"
    version = "1.0-stable1"
    description = "LZHAM - Lossless Data Compression Codec (lzham 1.0-stable1)"
    license = "MIT"
    homepage = "https://github.com/richgel999/lzham_codec"
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
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_X64"] = "ON"
        # Upstream CMakeLists requires cmake_minimum_required(2.8); CMake >= 3.5
        # removed old compatibility. Keep the policy override minimal.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        # Library targets: lzhamdecomp (core), lzhamcomp, lzhamdll (API facade)
        self.cpp_info.libs = ["lzhamdll", "lzhamcomp", "lzhamdecomp"]
        self.cpp_info.requires = []