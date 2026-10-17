#!/usr/bin/env python3
"""Conan recipe — libpopcnt 2.0 (CMake, header-only).

libpopcnt is a header-only C/C++ library (single `libpopcnt.h`) for counting
the number of 1 bits in an array using POPCNT/AVX2/AVX512/NEON. Upstream CMake
installs only the header; no binary is produced.

Bootstrap skeleton: source URL and SHA-256 verified from the official v2.0
release tarball. NOT yet compiled/validated in the OpenHarmony PC pipeline.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class LibpopcntConan(ConanFile):
    name = "libpopcnt"
    version = "2.0"
    description = "Fast C/C++ bit population count library (header-only)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/kimwalisch/libpopcnt"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        # header-only library: all settings combinations produce identical content
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # R32: platform check must use `in ("Linux", "OHOS")`, not `== "Linux"`
        if self.settings.os in ("Linux", "OHOS"):
            # E092: CMake doesn't recognize OHOS as a target platform
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # 上游 CMakeLists.txt 用 cmake_minimum_required(VERSION 2.8)，CMake >= 4
        # 已移除 <3.5 兼容。必须用 cache_variables 以 `-D` 传入，使该策略在解析
        # 上游 cmake_minimum_required 之前生效（写 toolchain 文件不生效）。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        # Header-only: upstream adds test executables (test1/test2); the
        # upstream test suite requires a runnable target. First-round Adapt
        # will decide whether cross-compiling/running upstream tests is
        # applicable before finalizing this step.
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libpopcnt")
        self.cpp_info.set_property("cmake_target_name", "libpopcnt::libpopcnt")
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]