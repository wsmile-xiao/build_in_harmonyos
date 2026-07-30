#!/usr/bin/env python3
"""Conan recipe — libtiff 4.6.0 (CMake build system).

TIFF image format library. Depends on zlib and libjpeg.
Source: https://gitlab.com/libtiff/libtiff
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibtiffConan(ConanFile):
    name = "libtiff"
    version = "4.6.0"
    description = "TIFF image format library"
    license = "libtiff"
    homepage = "https://libtiff.gitlab.io/libtiff/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("libjpeg/10")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.x compatibility
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # E092: CMake does not recognize HarmonyOS, use Linux for compatibility
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            _arch_map = {"armv8": "aarch64", "x86_64": "x86_64"}
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = _arch_map.get(
                str(self.settings.arch), str(self.settings.arch))
        # Static build
        if not self.options.shared:
            tc.cache_variables["BUILD_SHARED_LIBS"] = "OFF"
        # Disable optional dependencies not available on OHOS
        tc.cache_variables["jbig"] = "OFF"
        tc.cache_variables["lerc"] = "OFF"
        tc.cache_variables["lzma"] = "OFF"
        tc.cache_variables["zstd"] = "OFF"
        tc.cache_variables["webp"] = "OFF"
        tc.cache_variables["deflate"] = "OFF"
        # Disable docs and tests
        tc.cache_variables["tiff-docs"] = "OFF"
        tc.cache_variables["tiff-tests"] = "OFF"
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
        self.cpp_info.libs = ["tiff", "tiffxx"]
        # pkg-config support
        self.cpp_info.set_property("pkg_config_name", "libtiff-4")
