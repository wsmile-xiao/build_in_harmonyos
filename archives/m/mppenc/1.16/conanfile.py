#!/usr/bin/env python3
"""Conan recipe for mppenc 1.16 (Musepack SV7 encoder CLI)."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class MppencConan(ConanFile):
    name = "mppenc"
    version = "1.16"
    description = "Command-line Musepack (MPC) SV7 lossless audio encoder"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.musepack.net/"
    url = "https://www.musepack.net/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS", "Windows"):
            raise ConanInvalidConfiguration("mppenc supports Linux, OHOS, and Windows targets")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream declares cmake_minimum_required(VERSION 2.4); CMake >= 4 refuses < 3.5
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
