#!/usr/bin/env python3
"""Conan recipe — toml11 4.4.0 (CMake, header-only)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Toml11Conan(ConanFile):
    name = "toml11"
    version = "4.4.0"
    description = "C++11 header-only TOML parser/encoder/decoder"
    license = "MIT"
    homepage = "https://github.com/ToruNiina/toml11"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

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
        tc.variables["TOML11_INSTALL"] = "ON"
        tc.variables["TOML11_BUILD_TESTS"] = "OFF"
        tc.variables["TOML11_BUILD_EXAMPLES"] = "OFF"
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
