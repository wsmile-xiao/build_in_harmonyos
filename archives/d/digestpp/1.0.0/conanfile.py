#!/usr/bin/env python3
"""Conan recipe for digestpp 1.0.0 (CMake, header-only)."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class DigestppConan(ConanFile):
    name = "digestpp"
    version = "1.0.0"
    description = ("C++11 header-only message digest library supporting BLAKE, BLAKE2, "
                   "BLAKE3, Groestl, JH, Keccak, SHA-1/SHA-2/SHA-3, SHAKE, SM3, Skein, "
                   "Streebog, Whirlpool and many more hash algorithms.")
    license = "MIT"
    homepage = "https://github.com/kerukuro/digestpp"
    url = "https://github.com/kerukuro/digestpp"

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
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "digestpp")
        self.cpp_info.set_property("cmake_target_name", "digestpp::digestpp")
        self.cpp_info.includedirs = ["include"]