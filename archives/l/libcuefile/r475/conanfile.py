#!/usr/bin/env python3
"""Conan recipe for libcuefile r475."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibcuefileConan(ConanFile):
    name = "libcuefile"
    version = "r475"
    description = "Library to work with CUE files"
    license = "GPL-2.0-or-later"
    homepage = "https://www.musepack.net/"
    url = homepage
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["cuefile"]
        self.cpp_info.set_property("cmake_file_name", "libcuefile")
        self.cpp_info.set_property("cmake_target_name", "libcuefile::libcuefile")
