#!/usr/bin/env python3
"""Conan recipe — enchantum 0.4.0.

Fast macro-free enum reflection C++17 library (header-only, CMake INTERFACE).

Build system: CMake (upstream install() exports headers + CMake package config).
No third-party runtime dependencies (test-only deps: Catch2, {fmt}).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class EnchantumConan(ConanFile):
    name = "enchantum"
    version = "0.4.0"
    description = "Fast macro-free enum reflection C++ library"
    license = "MIT"
    homepage = "https://github.com/ZXShady/enchantum"
    url = "https://github.com/ZXShady/enchantum"
    topics = ("enum", "reflection", "header-only", "c++17", "bitflags")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Tests/benchmarks are optional and not part of the packaged library
        tc.variables["ENCHANTUM_BUILD_TESTS"] = "OFF"
        tc.variables["ENCHANTUM_BUILD_BENCHMARKS"] = "OFF"
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
        # Header-only: no link libraries, no binary dirs
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "enchantum")
        self.cpp_info.set_property("cmake_target_name", "enchantum::enchantum")

    # Header-only: same headers for any configuration
    def package_id(self):
        self.info.clear()
