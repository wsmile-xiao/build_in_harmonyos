#!/usr/bin/env python3
"""Conan recipe — liblaxjson 1.0.5 (CMake project).

Relaxed streaming JSON parser C library.
Source: https://github.com/andrewrk/liblaxjson
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LiblaxjsonConan(ConanFile):
    name = "liblaxjson"
    version = "1.0.5"
    description = "Relaxed streaming JSON parser C library"
    license = "MIT"
    homepage = "https://github.com/andrewrk/liblaxjson"
    url = ""  # CI fills this

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
        # CMake 4.x compatibility: upstream project declares cmake_minimum_required(2.8),
        # which CMake >= 3.5 refuses to configure. Patch applied to source already,
        # keep policy fallback for robustness.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # E092: CMake does not recognize HarmonyOS, use Linux for compatibility
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # R32: recipe supports both Linux and OHOS via settings
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
        self.cpp_info.libs = ["laxjson"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("pkg_config_name", "laxjson")
