#!/usr/bin/env python3
"""Conan recipe for cbmconvert 2.1.6 — Commodore archive converter tools.

Upstream builds with CMake (no OHOS platform module, so the toolchain
presents a generic Linux/aarch64 host). The official 6-test CTest suite runs
inside build() via cmake.test(); packaging installs cbmconvert, zip2disk and
disk2zip with their manpages.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class CbmconvertConan(ConanFile):
    name = "cbmconvert"
    version = "2.1.6"
    description = "Create, extract and convert 8-bit Commodore binary archives (cbmconvert, zip2disk, disk2zip)"
    license = "GPL-2.0-only"
    homepage = "https://github.com/dr-m/cbmconvert"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS must be accepted alongside Linux
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cbmconvert requires a POSIX host (Linux or OHOS), got {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # CMake has no OHOS platform module. The package builds natively on
        # OHOS with clang and uses only portable C + libc, so present the
        # host as generic Linux/aarch64 (same approach as the merged
        # abcmidi recipe).
        if self.settings.os in ("Linux", "OHOS"):
            toolchain.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            toolchain.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        toolchain.variables["BUILD_TESTING"] = True
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
