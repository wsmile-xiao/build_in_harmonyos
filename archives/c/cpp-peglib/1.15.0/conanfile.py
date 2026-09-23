#!/usr/bin/env python3
"""Conan recipe for cpp-peglib 1.15.0 (C++17 header-only PEG library)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches, get, unzip


required_conan_version = ">=2.0"

# Upstream test/CMakeLists.txt fetches GoogleTest via FetchContent from a
# hard-coded github.com URL. CI workers cannot reach github.com directly
# (the source URL is mirrored by the CI pipeline, but FetchContent is not),
# so we pre-download GoogleTest through the same mirror and hand it to
# FetchContent via FETCHCONTENT_SOURCE_DIR_GOOGLETEST.
GOOGLETEST_SHA = "03597a01ee50ed33e9dfd640b249b4be3799d395"
GOOGLETEST_URL = (
    "https://gh-proxy.com/https://github.com/google/googletest/archive/"
    + GOOGLETEST_SHA + ".zip"
)


class CppPeglibConan(ConanFile):
    name = "cpp-peglib"
    version = "1.15.0"
    package_type = "header-library"

    description = "A single-file C++17 header-only PEG parsing library"
    homepage = "https://yhirose.github.io/cpp-peglib/"
    license = "MIT"
    url = "https://github.com/yhirose/cpp-peglib"
    topics = ("parser", "peg", "header-only", "cpp17")

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = 17
        tc.variables["CMAKE_CXX_EXTENSIONS"] = False
        tc.variables["BUILD_TESTS"] = True
        tc.variables["PEGLIB_BUILD_BENCHMARK"] = False
        tc.variables["PEGLIB_BUILD_EXAMPLES"] = False
        tc.variables["PEGLIB_BUILD_LINT"] = False
        tc.variables["PEGLIB_BUILD_PL0"] = False
        # Point upstream FetchContent at the pre-downloaded GoogleTest source
        # (see GOOGLETEST_URL above) so tests build without github.com access.
        tc.variables["FETCHCONTENT_SOURCE_DIR_GOOGLETEST"] = self._gtest_src_dir()
        tc.generate()

    def _gtest_src_dir(self):
        return os.path.join(self.build_folder, "gtest-src",
                            "googletest-" + GOOGLETEST_SHA)

    def build(self):
        apply_conandata_patches(self)
        # Pre-download GoogleTest for upstream FetchContent (mirror first,
        # direct github.com as fallback).
        gtest_zip = os.path.join(self.build_folder, "gtest.zip")
        gtest_root = os.path.join(self.build_folder, "gtest-src",
                                  "googletest-" + GOOGLETEST_SHA)
        if not os.path.isdir(gtest_root):
            try:
                download(self, GOOGLETEST_URL, gtest_zip)
            except Exception:
                download(self,
                         "https://github.com/google/googletest/archive/"
                         + GOOGLETEST_SHA + ".zip", gtest_zip)
            unzip(self, gtest_zip, destination=os.path.join(self.build_folder, "gtest-src"))
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream official tests: one GoogleTest executable discovered as
        # individual CTest cases by gtest_discover_tests().
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "cpp-peglib")
        self.cpp_info.set_property("cmake_target_name", "cpp-peglib::cpp-peglib")

    def package_id(self):
        # The package contains only a source header and is independent of the
        # host compiler, build type, and architecture.
        self.info.clear()
