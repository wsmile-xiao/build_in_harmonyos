#!/usr/bin/env python3
"""Conan recipe for GmSSL 3.1.1 — national cipher algorithms (SM2/SM3/SM4/SM9)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class GmsslConan(ConanFile):
    name = "gmssl"
    version = "3.1.1"
    description = "GmSSL — cryptographic library supporting SM2/SM3/SM4/SM9 national cipher algorithms, OpenSSL-compatible API"
    license = "Apache-2.0"
    homepage = "https://github.com/guanzhi/GmSSL"
    url = "https://github.com/guanzhi/GmSSL"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

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
        self.cpp_info.libs = ["gmssl"]
        self.cpp_info.bindirs = ["bin"]
