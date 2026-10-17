#!/usr/bin/env python3
"""Conan recipe — is_utf8 1.4.1 (CMake project, static-only library).

is_utf8 is a single-unit SIMD-accelerated UTF-8 validation library
(https://github.com/simdutf/is_utf8). Upstream builds exactly one STATIC
library (src/CMakeLists.txt: add_library(is_utf8 STATIC ...)), so this
recipe declares package_type = "static-library" and offers no shared option.
"""
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout, CMakeToolchain
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class IsUtf8Conan(ConanFile):
    name = "is_utf8"
    version = "1.4.1"
    description = "Fast SIMD-accelerated UTF-8 validation function (single source file)"
    license = "Apache-2.0 OR BSL-1.0 OR MIT"
    homepage = "https://github.com/simdutf/is_utf8"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Run the upstream ctest suite inside build() only when host binaries
        # are executable here (native device build / same-platform CI).
        tc.variables["BUILD_TESTING"] = "ON" if can_run(self) else "OFF"
        # 0001-CMakeLists.txt.patch guards add_subdirectory(benchmarks); keep
        # it OFF: the benchmark target fetches simdutf from GitHub via
        # file(DOWNLOAD) at configure time, which must not run in CI.
        tc.variables["IS_UTF8_BUILD_BENCHMARKS"] = "OFF"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            # Layer 1: upstream official tests (tests/unit.cpp via ctest):
            # 42 hard-coded checks + 10,000 x (1 + 1000) differential
            # comparisons against the reference validator.
            cmake.test()

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE-*", dst="licenses", src=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["is_utf8"]
        self.cpp_info.set_property("cmake_file_name", "is_utf8")
        self.cpp_info.set_property("cmake_target_name", "is_utf8::is_utf8")
