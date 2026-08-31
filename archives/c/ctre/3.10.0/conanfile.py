#!/usr/bin/env python3
"""Conan recipe — ctre 3.10.0

CTRE (Compile Time Regular Expressions) — header-only C++17/20 template library
for compile-time regular expressions. No compilation needed; the package installs
the public headers under include/ and exposes the INTERFACE-style target.

License: Apache-2.0 with LLVM exception
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class CtreConan(ConanFile):
    name = "ctre"
    version = "3.10.0"
    description = "Compile Time Regular Expressions for C++17/20 (header-only)"
    license = "Apache-2.0-with-LLVM-exception"
    homepage = "https://github.com/hanickadot/compile-time-regular-expressions"
    url = "https://github.com/hanickadot/compile-time-regular-expressions"
    topics = ("regex", "template", "header-only", "compile-time")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        copy(self, "*.hpp", dst=os.path.join(self.package_folder, "include"), src=os.path.join(self.source_folder, "include"))
        copy(self, "*.gram", dst=os.path.join(self.package_folder, "include"), src=os.path.join(self.source_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ctre")
        self.cpp_info.set_property("cmake_target_name", "ctre::ctre")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []