#!/usr/bin/env python3
"""Conan recipe — refl-cpp 0.9.1 (header-only library).

refl-cpp is a single-header (refl.hpp) compile-time reflection library
for C++17. No build system, no compiled artifacts: package copies the
single header + license into the Conan package.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ReflcppConan(ConanFile):
    name = "refl-cpp"
    version = "0.9.1"
    description = "Compile-time reflection library for modern C++ (header-only)"
    license = "MIT"
    homepage = "https://github.com/veselink1/refl-cpp"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Header-only: nothing to compile (R34 test_package uses the header)

    def package(self):
        copy(self, "refl.hpp", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "refl-cpp")
        self.cpp_info.set_property("cmake_target_name", "refl-cpp::refl-cpp")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
