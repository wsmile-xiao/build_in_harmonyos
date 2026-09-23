#!/usr/bin/env python3
"""Conan recipe — utf8.h 0.0-git20260825.7e403ccc3f (header-only, CTest).

utf8.h is a single-header UTF-8 string library (Unlicense). It ships no build
system for the library itself: `utf8.h` is simply copied into the consumer's
include path. The upstream `test/` directory is a self-contained CMake+CTest
project (vendored utest.h, 487 atomic test cases, 8 CTest targets including
ASan/UBSan/TSan variants), driven here through the `run_upstream_tests`
option so CI and the device run the same suite (R51).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class Utf8HConan(ConanFile):
    name = "utf8.h"
    version = "0.0-git20260825.7e403ccc3f"
    description = "Single-header UTF-8 string functions (utf8len/utf8codepoint/utf8cat/...)"
    license = "Unlicense"
    homepage = "https://github.com/sheredom/utf8.h"
    url = "https://github.com/sheredom/utf8.h"
    topics = ("utf8", "unicode", "header-only", "string")
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"run_upstream_tests": [True, False]}
    default_options = {"run_upstream_tests": True}

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        self.info.clear()

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos", "FreeBSD"):
            raise ConanInvalidConfiguration(
                f"utf8.h not validated for {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 test/CMakeLists.txt 声明 cmake_minimum_required(VERSION 3.15)；
        # 保持工具链变量显式，避免 CMake 4 的 policy 兼容问题。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if not self.options.run_upstream_tests:
            return
        # 上游 test/ 是自包含 CMake 工程（vendored utest.h），源码根即 include 根。
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "test"))
        cmake.build()
        if can_run(self):
            cmake.test()

    def package(self):
        copy(self, "utf8.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
