#!/usr/bin/env python3
"""
Conan recipe for cJSON v1.7.19 — OHOS (OpenHarmony) aarch64 adaptation.

Portability patches: cmake_minimum_required 3.0→3.5, C standard c89→c99.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class CjsonConan(ConanFile):
    name = "cjson"
    version = "1.7.19"
    description = "Ultralightweight JSON parser in ANSI C"
    license = "MIT"
    homepage = "https://github.com/DaveGamble/cJSON"
    url = "https://github.com/DaveGamble/cJSON"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["ENABLE_CJSON_TEST"] = "OFF"
        tc.variables["ENABLE_CJSON_UTILS"] = "OFF"  # upstream utils not needed for OHOS
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["cjson"]