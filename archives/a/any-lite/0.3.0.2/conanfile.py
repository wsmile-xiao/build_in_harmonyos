#!/usr/bin/env python3
"""Conan recipe for any-lite 0.3.0.2 (CMake header-only library, upstream v0.3.0).

nonstd::any-lite is a C++17-like any, a type-safe container for single
values of any type for C++98, C++11 and later in a single-file header-only
library. Zero dependencies; the upstream test suite uses the vendored lest
framework (test/lest_cpp03.hpp), so no network access is needed for testing.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class AnyLiteConan(ConanFile):
    name = "any-lite"
    version = "0.3.0.2"
    description = "A C++17-like any, a type-safe container for single values of any type for C++98, C++11 and later in a single-file header-only library"
    license = "BSL-1.0"
    homepage = "https://github.com/martinmoene/any-lite"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/a/any-lite/0.3.0.2"
    topics = ("any", "header-only", "cpp98", "cpp11", "cpp17")
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"run_upstream_tests": [True, False]}
    default_options = {"run_upstream_tests": True}

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        self.info.clear()

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos", "FreeBSD"):
            raise ConanInvalidConfiguration(f"{self.name} not validated for {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["ANY_LITE_OPT_BUILD_TESTS"] = bool(self.options.run_upstream_tests)
        tc.cache_variables["ANY_LITE_OPT_BUILD_EXAMPLES"] = False
        tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.options.run_upstream_tests:
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
            if can_run(self):
                cmake.test()

    def package(self):
        copy(self, "any.hpp", src=os.path.join(self.source_folder, "include", "nonstd"),
             dst=os.path.join(self.package_folder, "include", "nonstd"))
        # 上游 CMake install 不安装 LICENSE.txt，配方显式补齐
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "any-lite")
        self.cpp_info.set_property("cmake_target_name", "nonstd::any-lite")
