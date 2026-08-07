#!/usr/bin/env python3
"""Conan recipe for nghttp3 1.15.0 — HTTP/3 library.

nghttp3 is an HTTP/3 library written in C, implementing the RFC 9114 specification.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Nghttp3Conan(ConanFile):
    name = "nghttp3"
    version = "1.15.0"
    description = "nghttp3 is an HTTP/3 library written in C"
    license = "MIT"
    homepage = "https://github.com/ngtcp2/nghttp3"
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
        tc.variables["NGHTTP3_BUILD_LIBS_ONLY"] = "OFF"
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
        self.cpp_info.libs = ["nghttp3"]
