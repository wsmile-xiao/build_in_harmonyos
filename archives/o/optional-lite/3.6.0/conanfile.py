#!/usr/bin/env python3
"""Conan recipe for optional-lite 3.6.0.

nonstd::optional-lite is a C++17-like optional, a nullable object for C++98,
C++11 and later in a single-file header-only library. Zero dependencies; the
upstream test suite uses the vendored lest framework (test/lest/lest_cpp03.hpp),
so no network access is needed for testing.

3.6.0 adds the value_or_eval() extension API (available in the nonstd backport
mode, i.e. when optional_CONFIG_NO_EXTENSIONS is not set and std::optional is
not selected).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class OptionalLiteConan(ConanFile):
    name = "optional-lite"
    version = "3.6.0"
    description = "A C++17-like optional, a nullable object for C++98, C++11 and later in a single-file header-only library"
    license = "BSL-1.0"
    homepage = "https://github.com/nonstd-lite/optional-lite"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/o/optional-lite/3.6.0"
    topics = ("optional", "header-only", "cpp98", "cpp11", "cpp17")
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
        tc.cache_variables["OPTIONAL_LITE_OPT_BUILD_TESTS"] = bool(self.options.run_upstream_tests)
        tc.cache_variables["OPTIONAL_LITE_OPT_BUILD_EXAMPLES"] = False
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
        copy(self, "optional.hpp", src=os.path.join(self.source_folder, "include", "nonstd"),
             dst=os.path.join(self.package_folder, "include", "nonstd"))
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "optional-lite")
        self.cpp_info.set_property("cmake_target_name", "nonstd::optional-lite")
