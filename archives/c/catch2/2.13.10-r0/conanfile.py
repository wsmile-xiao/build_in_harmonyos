#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class Catch2Conan(ConanFile):
    name = "catch2"
    version = "2.13.10-r0"
    description = "A modern, C++-native test framework"
    license = "BSL-1.0"
    homepage = "https://github.com/catchorg/Catch2"
    url = ""
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "single_include", "catch2"), dst=os.path.join(self.package_folder, "include", "catch2"))
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Catch2")
        self.cpp_info.set_property("cmake_target_name", "Catch2::Catch2")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
