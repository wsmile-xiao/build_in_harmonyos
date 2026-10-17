#!/usr/bin/env python3
"""Conan recipe — libsmb2 6.2 (CMake build).

libsmb2 is a client library for accessing SMB shares via SMB2/SMB3 protocol.
Pure C implementation, no external dependencies (only libc).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Libsmb2Conan(ConanFile):
    name = "libsmb2"
    version = "6.2"
    description = "Client library for accessing SMB shares via SMB2/SMB3 protocol"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/sahlberg/libsmb2"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libsmb2 has no mandatory external dependencies
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # libsmb2 is NOT a system same-name library -> shared build (R26 N/A)
        # Build shared library
        tc.variables["BUILD_SHARED_LIBS"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Copy license
        copy(self, "LICENCE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["smb2"]
        # Headers are installed under include/smb2/
        self.cpp_info.includedirs.append(os.path.join("include", "smb2"))
        # R32: platform check must use in ("Linux", "OHOS")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["c"]
