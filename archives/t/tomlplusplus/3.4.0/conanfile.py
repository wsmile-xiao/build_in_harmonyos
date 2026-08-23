#!/usr/bin/env python3
"""Conan recipe for tomlplusplus 3.4.0 — header-only C++ TOML parser.

Uses upstream CMake install rules (INTERFACE library, headers + cmake config).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TomlplusplusConan(ConanFile):
    name = "tomlplusplus"
    version = "3.4.0"
    description = "Header-only TOML parser and serializer for C++ (TOML 1.0 compliant)"
    license = "MIT"
    homepage = "https://github.com/marzer/tomlplusplus"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
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
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
