#!/usr/bin/env python3
"""Conan recipe — jsoncons 1.9.0 (header-only C++17/20 JSON library).

jsoncons by Daniel Parker — JSON data format library: parsing/serialization,
JSON Patch / Merge Patch, JMESPath, CSV, CBOR, MessagePack, etc. Header-only
under include/jsoncons/, installed via CMake INTERFACE library (jsoncons).
"""
import os

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class JsonconsConan(ConanFile):
    name = "jsoncons"
    version = "1.9.0"
    description = "jsoncons — a C++17/20 JSON data format library (parse/serialize, JSON Patch, JMESPath, CBOR, MessagePack), header-only"
    license = "BSL-1.0"
    homepage = "https://github.com/danielaparker/jsoncons"
    url = ""  # CI fills this
    topics = ("json", "serialization", "header-only", "cpp17", "cpp20", "jmespath")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        # NOTE: do NOT use cmake_layout() here. With no_copy_source=True,
        # cmake_layout remaps self.source_folder to the recipe export dir,
        # which makes package() copy() find no sources ("No files in this
        # package!"). An empty layout keeps self.source_folder pointing at the
        # downloaded source tree (cache .../s), where include/ lives.
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Header-only library: no compilation step; headers are packaged as-is.
        # build() exists to satisfy G1 recipe-completeness gate (no-op for
        # header-only libraries without a real build step).
        pass

    def package(self):
        # jsoncons installs include/jsoncons/ + include/jsoncons_ext/ (header-only).
        # Use a recursive "*" pattern: a bare directory-name pattern does not
        # match, leaving the package empty ("No files in this package!").
        copy(self, "*",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "jsoncons")
        self.cpp_info.set_property("cmake_target_name", "jsoncons::jsoncons")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # Header-only library: no libs to link.
        self.cpp_info.libs = []