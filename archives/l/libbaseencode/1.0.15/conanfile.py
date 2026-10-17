#!/usr/bin/env python3
"""Conan recipe for libbaseencode 1.0.15 — CMake build system.

libbaseencode (paolostivanin) is a C library implementing RFC-4648
base32/base64 encode/decode. The official build system is CMake
(CMakeLists.txt at repo root), NOT autotools.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibbaseencodeConan(ConanFile):
    name = "libbaseencode"
    version = "1.0.15"
    description = "Library written in C for encoding and decoding data using base32 or base64 (RFC-4648)"
    license = "MIT"
    homepage = "https://github.com/paolostivanin/libbaseencode"
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
        # R26: system-name libs default to static; libbaseencode is not a
        # system lib, but static keeps the package self-contained on OHOS.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
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
        self.cpp_info.set_property("cmake_file_name", "libbaseencode")
        self.cpp_info.set_property("cmake_target_name", "baseencode")
        self.cpp_info.set_property("pkg_config_name", "baseencode")
        self.cpp_info.libs = ["baseencode"]
