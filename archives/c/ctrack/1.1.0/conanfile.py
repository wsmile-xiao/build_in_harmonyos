#!/usr/bin/env python3
"""Conan recipe for ctrack 1.1.0 — header-only CMake library.

ctrack is a single-header C++17 benchmarking/profiling library
(include/ctrack.hpp). No compiled artifacts: package copies the public
header plus the CMake package config installed by the upstream
CMakeLists.txt (find_package(ctrack) + ctrack::ctrack target).

OHOS adaptation: upstream uses std::execution (parallel execution policy)
which is not available in the OHOS libc++ toolchain. Upstream CMakeLists
itself defines CTRACK_DISABLE_EXECUTION_POLICY whenever TBB is not found
(no TBB on OHOS either), so the same official compile definition is
propagated to consumers via cpp_info.defines. Single-header consumers
compile without any extra flags beyond this define.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class CtrackConan(ConanFile):
    name = "ctrack"
    version = "1.1.0"
    description = "Lightweight high-performance C++ benchmarking and tracking library (single-header)"
    license = "MIT"
    homepage = "https://github.com/Compaile/ctrack"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    no_copy_source = True

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.variables["BUILD_BENCHMARK"] = "OFF"
        tc.variables["DISABLE_EXAMPLES"] = "ON"
        tc.generate()

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only: configure the CMake package config so consumers get
        # find_package(ctrack)/ctrack::ctrack support.
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={
            "BUILD_TESTS": "OFF",
            "BUILD_BENCHMARK": "OFF",
            "DISABLE_EXAMPLES": "ON",
        })
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        # Header-only: no compiled artifacts, single package for all configs.
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # Upstream CMakeLists defines this whenever TBB is unavailable;
        # required on OHOS where std::execution does not exist.
        self.cpp_info.defines = ["CTRACK_DISABLE_EXECUTION_POLICY"]
        self.cpp_info.set_property("cmake_file_name", "ctrack")
        self.cpp_info.set_property("cmake_target_name", "ctrack::ctrack")