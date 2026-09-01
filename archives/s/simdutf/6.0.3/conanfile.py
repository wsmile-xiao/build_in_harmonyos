#!/usr/bin/env python3
"""Conan recipe — simdutf 6.0.3 (CMake project, static library)."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class SimdutfConan(ConanFile):
    name = "simdutf"
    version = "6.0.3"
    description = "Unicode (UTF-8) validation and transcoding library, fast and SIMD-accelerated"
    license = "MIT"
    homepage = "https://github.com/simdutf/simdutf"
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
        # R26: system-name library -> static by default
        tc.variables["BUILD_SHARED_LIBS"] = "OFF" if not self.options.shared else "ON"
        tc.variables["SIMDUTF_TOOLS"] = "OFF"
        tc.variables["SIMDUTF_TESTS"] = "OFF"
        tc.variables["SIMDUTF_BENCHMARKS"] = "OFF"
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
        self.cpp_info.libs = ["simdutf"]
        self.cpp_info.set_property("cmake_file_name", "simdutf")
        self.cpp_info.set_property("cmake_target_name", "simdutf::simdutf")
