#!/usr/bin/env python3
"""Conan recipe for variant-lite 3.0.0 (CMake header-only library)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class VariantLiteConan(ConanFile):
    name = "variant-lite"
    version = "3.0.0"
    description = "A C++17-like variant for C++98, C++11 and later in a single-file header-only library"
    license = "BSL-1.0"
    homepage = "https://github.com/martinmoene/variant-lite"
    url = "https://github.com/martinmoene/variant-lite"
    topics = ("variant", "header-only", "cpp11", "cpp17")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        elif self.settings.os == "Linux":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.variables["VARIANT_LITE_OPT_BUILD_TESTS"] = True
        tc.variables["VARIANT_LITE_OPT_BUILD_EXAMPLES"] = False
        tc.variables["VARIANT_LITE_OPT_SELECT_NONSTD"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "variant-lite")
        self.cpp_info.set_property("cmake_target_name", "nonstd::variant-lite")
        self.cpp_info.libs = []
