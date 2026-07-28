#!/usr/bin/env python3
"""Conan recipe — xtensor 0.25.0 (header-only CMake INTERFACE library)."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class XtensorConan(ConanFile):
    name = "xtensor"
    version = "0.25.0"
    description = "C++ tensors with broadcasting and lazy computing"
    license = "BSD-3-Clause"
    homepage = "https://github.com/xtensor-stack/xtensor"
    url = ""

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("xtl/0.7.7")
        self.requires("xsimd/13.2.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("xtl", "cmake_file_name", "xtl")
        deps.set_property("xtl", "cmake_target_name", "xtl")
        deps.set_property("xsimd", "cmake_file_name", "xsimd")
        deps.set_property("xsimd", "cmake_target_name", "xsimd")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.cache_variables["XTENSOR_USE_XSIMD"] = "ON"
        tc.cache_variables["XTENSOR_USE_OPENMP"] = "OFF"
        tc.cache_variables["XTENSOR_USE_TBB"] = "OFF"
        tc.cache_variables["BUILD_TESTS"] = "OFF"
        tc.cache_variables["BUILD_BENCHMARK"] = "OFF"
        tc.cache_variables["DOWNLOAD_GTEST"] = "OFF"
        tc.cache_variables["DOWNLOAD_GBENCHMARK"] = "OFF"
        # E191: header-only package, avoid executable try-link on OHOS.
        tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
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
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = ["xtl::xtl", "xsimd::xsimd"]
        self.cpp_info.set_property("cmake_file_name", "xtensor")
        self.cpp_info.set_property("cmake_target_name", "xtensor")
        self.cpp_info.set_property("pkg_config_name", "xtensor")
