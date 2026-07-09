#!/usr/bin/env python3
"""Conan recipe for qrencode 4.1.1 — QR Code encoding library and CLI tool."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QrencodeConan(ConanFile):
    name = "qrencode"
    version = "4.1.1"
    description = "Fast and compact QR Code encoding library"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/fukuchi/libqrencode"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["WITH_TESTS"] = "YES"
        tc.variables["WITHOUT_PNG"] = "YES"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["qrencode"]
