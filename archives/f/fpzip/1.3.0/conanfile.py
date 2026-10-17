#!/usr/bin/env python3
"""Conan recipe — fpzip 1.3.0 (CMake, library).

fpzip is a compact compressor for floating-point arrays (LLNL).
CMake build; installs header, shared/static lib and CMake config.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class FpzipConan(ConanFile):
    name = "fpzip"
    version = "1.3.0"
    description = "fpzip 1.3.0: library for compressing arrays of floating-point values"
    license = "MIT"
    homepage = "https://github.com/LLNL/fpzip"
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
        # R26: system-name libraries default to static; fpzip is not a system
        # lib but keep shared toggle explicit.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Upstream declares cmake_minimum_required(3.1); CMake >= 4 removed
        # compatibility with < 3.5. Pass as a cache variable (-D) so it is
        # consulted before the project's minimum version is enforced.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # errno-safe floating-point conversions (matches validated build)
        tc.variables["FPZIP_FP"] = "FPZIP_FP_SAFE"
        # fpzipcmd has no install rule upstream; build only the library.
        tc.variables["BUILD_UTILITIES"] = "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
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
        self.cpp_info.libs = ["fpzip"]
        self.cpp_info.set_property("cmake_file_name", "fpzip")
        self.cpp_info.set_property("cmake_target_name", "fpzip::fpzip")