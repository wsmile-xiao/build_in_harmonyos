#!/usr/bin/env python3
"""Conan recipe for osslsigncode 2.13 — CMake-based Authenticode signing tool."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OsslsigncodeConan(ConanFile):
    name = "osslsigncode"
    version = "2.13"
    description = "OpenSSL-based code signing tool for Authenticode and PE/MSI/CAB/CAT/APPX files"
    license = "GPL-3.0"
    homepage = "https://github.com/mtrojnar/osslsigncode"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # HarmonyOS: CMake doesn't recognize OHOS as a UNIX platform,
        # so UNIX/APPLE/WIN32 are not set. Force UNIX=ON so that
        # Windows-only sources (applink.c) are excluded.
        tc.variables["UNIX"] = "ON"
        # Skip try-compile checks that fail under cross-compilation
        tc.variables["HAVE_SYS_MMAN_H"] = "ON"
        tc.variables["HAVE_MMAP"] = "ON"
        tc.variables["HAVE_GETPASS"] = "ON"
        tc.variables["HAVE_TERMIOS_H"] = "ON"
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
        self.cpp_info.bindirs = ["bin"]
