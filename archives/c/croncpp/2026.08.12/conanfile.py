#!/usr/bin/env python3
"""Conan recipe for croncpp 2026.08.12 — header-only C++ CRON expression library.

Upstream: https://github.com/mariusbancila/croncpp (MIT, tag v2026.08.12)
Build system: CMake INTERFACE (header-only). No runtime dependencies.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CroncppConan(ConanFile):
    name = "croncpp"
    version = "2026.08.12"
    description = "Header-only C++ library for parsing CRON expressions and computing next/previous occurrences"
    license = "MIT"
    homepage = "https://github.com/mariusbancila/croncpp"
    url = "https://github.com/mariusbancila/croncpp"
    topics = ("cron", "scheduling", "header-only", "cronexpr")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Header-only: upstream test suite is not part of the recipe build
        tc.variables["CRONCPP_BUILD_TESTS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        src = str(self.source_folder)
        copy(self, "croncpp.h",
             src=os.path.join(src, "include"),
             dst=os.path.join(str(self.package_folder), "include"))
        copy(self, "LICENSE",
             src=src,
             dst=str(self.package_folder))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "croncpp")
        self.cpp_info.set_property("cmake_target_name", "croncpp::croncpp")
        self.cpp_info.components["croncpp"].cxxflags = ["-std=c++17"]

    def package_id(self):
        # Header-only: single package regardless of settings
        self.info.clear()
