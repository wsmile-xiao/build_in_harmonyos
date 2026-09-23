#!/usr/bin/env python3
"""Conan recipe — libsimdpp 2.1 (header-only C++ SIMD library).

libsimdpp is a header-only C++11 SIMD abstractions library. The upstream
CMake project installs its headers under include/libsimdpp-2.1/simdpp/ plus a
pkg-config file; no binaries or libraries are produced (package_type
header-library).

Upstream declares cmake_minimum_required(VERSION 2.8.0), which CMake >= 4.x
rejects unless the minimum policy version is raised; CMAKE_POLICY_VERSION_MINIMUM
is set in the toolchain so downstream builds configure cleanly.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibsimdppConan(ConanFile):
    name = "libsimdpp"
    version = "2.1"
    description = "libsimdpp - portable vectorized C++ SIMD library (header-only)"
    license = "BSL-1.0"
    homepage = "https://github.com/p12tic/libsimdpp"
    url = "https://github.com/p12tic/libsimdpp"  # CI fills this

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
        # Upstream cmake_minimum_required(2.8) is incompatible with CMake >= 4.x
        # unless the minimum policy version is raised.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream simdpp/CMakeLists.txt installs headers with
        # file(GLOB_RECURSE ... *.h *.inl), which omits the required
        # detail/preprocessor/*.hpp headers; consumers fail to compile
        # (simdpp/setup_arch.h includes stringize.hpp). Copy them over.
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "simdpp"),
             dst=os.path.join(self.package_folder, "include/libsimdpp-2.1/simdpp"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libsimdpp")
        self.cpp_info.set_property("cmake_target_name", "libsimdpp::libsimdpp")
        self.cpp_info.includedirs = ["include/libsimdpp-2.1"]