#!/usr/bin/env python3
"""Conan recipe — zpp_bits 4.7.6 (header-only).

Modern C++20 binary serialization and RPC library, shipped as a single
header (zpp_bits.h). Zero dependencies, no build step: copy the header
into the package include/ and expose the cmake target.
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class ZppBitsConan(ConanFile):
    name = "zpp_bits"
    version = "4.7.6"
    package_type = "header-library"

    description = "A modern C++20 binary serialization and RPC library, with just one header file"
    homepage = "https://github.com/eyalz800/zpp_bits"
    license = "MIT"
    url = "https://github.com/eyalz800/zpp_bits"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Header-only library: no build step required.
        pass

    def package(self):
        copy(self, "zpp_bits.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "zpp_bits")
        self.cpp_info.set_property("cmake_target_name", "zpp_bits::zpp_bits")
        self.cpp_info.includedirs = ["include"]