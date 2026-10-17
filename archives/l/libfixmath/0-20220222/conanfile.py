#!/usr/bin/env python3
"""Conan recipe for libfixmath 0-20220222."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibfixmathConan(ConanFile):
    name = "libfixmath"
    version = "0-20220222"
    description = "Cross-platform Q16.16 fixed-point mathematics library"
    license = "MIT"
    homepage = "https://github.com/PetteriAimonen/libfixmath"
    url = "https://github.com/PetteriAimonen/libfixmath"
    topics = ("fixed-point", "mathematics", "embedded")
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = False
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "libfixmath"),
            dst=os.path.join(self.package_folder, "include", "libfixmath"),
            keep_path=False,
        )
        copy(
            self,
            "*.hpp",
            src=os.path.join(self.source_folder, "libfixmath"),
            dst=os.path.join(self.package_folder, "include", "libfixmath"),
            keep_path=False,
        )
        copy(
            self,
            "liblibfixmath.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["libfixmath"]
        self.cpp_info.set_property("cmake_file_name", "libfixmath")
        self.cpp_info.set_property("cmake_target_name", "libfixmath::libfixmath")
        self.cpp_info.set_property("pkg_config_name", "libfixmath")
