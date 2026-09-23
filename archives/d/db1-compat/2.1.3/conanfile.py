#!/usr/bin/env python3
"""Conan recipe for the DB 1.85 compatibility library from glibc 2.1.3."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Db1CompatConan(ConanFile):
    name = "db1-compat"
    version = "2.1.3"
    description = "Legacy Berkeley DB 1.85 compatibility library"
    license = "BSD-4-Clause"
    homepage = "https://www.gnu.org/software/libc/"
    url = "https://sourceware.org/git/glibc.git"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "db"))
        cmake.build(build_tool_args=["-j1"])

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.libs = ["db"]
        self.cpp_info.includedirs = ["include/db1"]
        self.cpp_info.set_property("cmake_file_name", "db1-compat")
        self.cpp_info.set_property("cmake_target_name", "db1-compat::db1-compat")
