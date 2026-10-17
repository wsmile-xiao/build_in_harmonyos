#!/usr/bin/env python3
"""Conan recipe for msgpack-cxx 6.1.1 — header-only C++ MessagePack library."""

import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class MsgpackcxxConan(ConanFile):
    name = "msgpack-cxx"
    version = "6.1.1"
    description = "MessagePack is an efficient binary serialization format for C++"
    license = "BSL-1.0"
    homepage = "https://github.com/msgpack/msgpack-c"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # Header-only libraries don't care about os.version; remove it safely
        if hasattr(self.settings, "os") and hasattr(self.settings.os, "version"):
            self.settings.rm_safe("os.version")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        # Copy all headers from include/ directory
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        # Also copy any other header files
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.defines = ["MSGPACK_NO_BOOST"]
        self.cpp_info.set_property("cmake_target_name", "msgpack-cxx::msgpack-cxx")
