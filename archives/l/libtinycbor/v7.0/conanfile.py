#!/usr/bin/env python3
"""Conan recipe — libtinycbor v7.0 (TinyCBOR CBOR encoding/decoding library).

CMake build. No external dependencies. Builds static library + cbordump tool.
OHOS adaptation: CMAKE_SYSTEM_NAME=HarmonyOS, BUILD_TESTING=OFF (Qt6 unavailable).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class LibtinycborConan(ConanFile):
    name = "libtinycbor"
    version = "v7.0"
    description = "Concise Binary Object Representation (CBOR) library"
    license = "MIT"
    homepage = "https://github.com/intel/tinycbor"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        # R32: settings.os judgment must use in ("Linux", "OHOS")
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "HarmonyOS"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch))
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["tinycbor"]
        self.cpp_info.bindirs = ["bin"]  # cbordump tool -> R38 commands.json
        # tinycbor links libm on non-Windows (floating point support)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
