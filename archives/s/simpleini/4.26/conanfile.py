#!/usr/bin/env python3
"""Conan recipe for simpleini 4.26 — header-only C++17 INI reader/writer.

simpleini is a single-file C++17 header (SimpleIni.h) exposing the
CSimpleIniA / CSimpleIniW classes. The upstream CMakeLists builds an
INTERFACE library that installs the header plus a CMake package config.
No compilation is needed for the library itself; tests are gtest-based
and are run separately (upstream_tests gate).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class SimpleiniConan(ConanFile):
    name = "simpleini"
    version = "4.26"
    description = "Cross-platform C++ library providing a simple API to read and write INI-style configuration files"
    license = "MIT"
    homepage = "https://github.com/brofield/simpleini"
    url = ""  # CI fills this
    topics = ("ini", "config", "header-only", "cpp", "csimpleini")

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
        # Upstream tests require GoogleTest (FetchContent); they are exercised
        # by the upstream_tests gate, not by the conan build.
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
        # Header-only: no libs/binaries to link or install.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "simpleini")
        self.cpp_info.set_property("cmake_target_name", "simpleini::simpleini")
