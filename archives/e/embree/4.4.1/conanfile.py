#!/usr/bin/env python3
"""Conan recipe for embree 4.4.1 — High-performance ray tracing kernels.

HarmonyOS ARM64 adaptation: static library, ARM NEON ISA, INTERNAL tasking system.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class EmbreeConan(ConanFile):
    name = "embree"
    version = "4.4.1"
    description = "High-performance ray tracing kernels for Intel processors (HarmonyOS ARM64 port)"
    license = "Apache-2.0"
    homepage = "https://github.com/RenderKit/embree"
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
        # Embree requires Release build type for correct SIMD code paths
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.variables["EMBREE_TASKING_SYSTEM"] = "INTERNAL"
        tc.variables["EMBREE_TUTORIALS"] = "OFF"
        tc.variables["EMBREE_ARM"] = "ON"
        tc.variables["EMBREE_ISA_NEON"] = "ON"
        tc.variables["EMBREE_ISA_NEON2X"] = "OFF"
        tc.variables["EMBREE_ISA_SSE2"] = "OFF"
        tc.variables["EMBREE_ISA_SSE42"] = "OFF"
        tc.variables["EMBREE_ISA_AVX"] = "OFF"
        tc.variables["EMBREE_ISA_AVX2"] = "OFF"
        tc.variables["EMBREE_STATIC_LIB"] = "ON"
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
        # embree4 depends on internal static libs: tasking, lexers, simd, math, sys
        self.cpp_info.libs = ["embree4", "tasking", "lexers", "simd", "math", "sys"]
        self.cpp_info.set_property("cmake_file_name", "embree")
        self.cpp_info.set_property("cmake_target_name", "embree::embree")
        self.cpp_info.system_libs = ["pthread"]
