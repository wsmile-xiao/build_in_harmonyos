#!/usr/bin/env python3
"""Conan recipe for PhysUnits-CT 0.1.0 (header-only C++98 library)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, download, export_conandata_patches, get


class PhysunitsCtConan(ConanFile):
    name = "physunits-ct"
    version = "0.1.0"
    description = "Header-only C++98 compile-time dimensional analysis and unit/quantity library"
    license = "BSL-1.0"
    homepage = "https://github.com/martinmoene/PhysUnits-CT"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # Keep the standard patch export hook for the patch pipeline.  The
        # single patch adds a CMake build layer; it touches no upstream file.
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The upstream test programs include "catch.hpp" through the ad-hoc
        # makefiles' CATCH_INCLUDE path; upstream ships no copy of it.  Fetch
        # the Catch v1 single header (Catch2 v1.12.2, BSL-1.0) into the source
        # root, where the patch-added CMakeLists.txt expects it.  Only used
        # when PHYS_UNITS_OPT_BUILD_TESTS=ON.
        url = self.conan_data["test_framework"]["url"]
        sha256 = self.conan_data["test_framework"]["sha256"]
        download(self, url, os.path.join(self.source_folder, "catch.hpp"), sha256=sha256)

    def generate(self):
        # Force the Ninja generator: on the current OHOS device make's own
        # exec of /bin/sh is denied by HMMAC policy, which breaks every
        # CMake "Unix Makefiles" try-compile.  Ninja spawns commands directly.
        self.conf.define("tools.cmake.cmaketoolchain:generator", "Ninja")
        tc = CMakeToolchain(self)

        # R32: the OHOS profile maps CMAKE_SYSTEM_NAME to HarmonyOS, which
        # device CMake 4.1 does not know.  Linux platform semantics are the
        # same as the sister package physunits-ct-cpp11/1.4.0 uses.
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"

        # Build the upstream Catch test suite (7 TUs -> 6 test binaries).
        tc.cache_variables["PHYS_UNITS_OPT_BUILD_TESTS"] = True
        tc.cache_variables["PHYS_UNITS_OPT_BUILD_EXAMPLES"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_id(self):
        # The package contains headers and a CMake interface target only.
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "PhysUnits-CT")
        self.cpp_info.set_property("cmake_target_name", "PhysUnits::PhysUnits")
