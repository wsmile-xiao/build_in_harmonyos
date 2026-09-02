#!/usr/bin/env python3
"""Conan recipe for optional 1.1.0.

tl::optional is a header-only C++11/14/17 std::optional implementation with
functional-style extensions and reference support. Upstream CMakeLists.txt
fetches Catch2 v2.9.2 via FetchContent; we patch it to use
find_package(Catch2) from the Conan catch2/2.13.10-r0 package instead.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class OptionalConan(ConanFile):
    name = "optional"
    version = "1.1.0"
    description = "C++11/14/17 std::optional with functional-style extensions and reference support"
    license = "CC0-1.0"
    homepage = "https://github.com/TartanLlama/optional"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/o/optional/1.1.0"
    topics = ("optional", "header-only", "cpp11", "cpp14", "cpp17")
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

    def requirements(self):
        if self.options.run_upstream_tests:
            self.requires("catch2/2.13.10-r0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["OPTIONAL_BUILD_TESTS"] = bool(self.options.run_upstream_tests)
        tc.cache_variables["OPTIONAL_BUILD_PACKAGE"] = False
        tc.cache_variables["BUILD_TESTING"] = bool(self.options.run_upstream_tests)
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
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "tl-optional")
        self.cpp_info.set_property("cmake_target_name", "tl::optional")
