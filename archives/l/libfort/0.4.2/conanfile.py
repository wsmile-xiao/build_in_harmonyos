#!/usr/bin/env python3
"""Conan recipe template — CMake projects.

Usage: Replace Libfort, libfort, 0.4.2, Simple crossplatform C/C++ library to create formatted ASCII tables for console applications, MIT, https://github.com/seleznevae/libfort
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: BUILD_SHARED_LIBS=OFF for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibfortConan(ConanFile):
    name = "libfort"
    version = "0.4.2"
    description = "Simple crossplatform C/C++ library to create formatted ASCII tables for console applications"
    license = "MIT"
    homepage = "https://github.com/seleznevae/libfort"
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
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 上游 cmake_minimum_required(VERSION 3.0) 与 CMake 4.x 不兼容 (E187)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["FORT_ENABLE_TESTING"] = "ON"
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
        # 上游 add_library(fort fort.c) → 输出 libfort.a/.so，链接名为 -lfort（pkg-config: -lfort）
        self.cpp_info.libs = ["fort"]
        self.cpp_info.set_property("pkg_config_name", "libfort")
        self.cpp_info.set_property("cmake_file_name", "libfort")
        self.cpp_info.set_property("cmake_target_name", "libfort::fort")
