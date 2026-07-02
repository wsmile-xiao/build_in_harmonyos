#!/usr/bin/env python3
"""Conan recipe — Monkey's Audio (mac) 12.60.

Monkey's Audio is a lossless audio codec (APE format).
Source: https://monkeysaudio.com
License: BSD-3-Clause
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MacConan(ConanFile):
    name = "mac"
    version = "12.60"
    description = "Monkey's Audio — lossless audio codec (APE format)"
    license = "BSD-3-Clause"
    homepage = "https://monkeysaudio.com"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mac supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        # verify=False: monkeysaudio.com SSL cert not trusted on OHOS
        # strip_root=False: SDK ZIP has multiple top-level items (no wrapping dir)
        get(self, **self.conan_data["sources"], strip_root=False, verify=False)

    def generate(self):
        tc = CMakeToolchain(self)
        # mac is NOT a system same-name library; build shared (default)
        tc.variables["BUILD_SHARED"] = True
        tc.variables["BUILD_UTIL"] = True
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
        self.cpp_info.libs = ["MAC"]
