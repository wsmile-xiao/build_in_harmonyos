#!/usr/bin/env python3
"""Conan recipe for the qwprot header-only protocol declarations."""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class QwprotConan(ConanFile):
    name = "qwprot"
    version = "0.0-28-20250208-07a7285"
    description = "Shared QuakeWorld network protocol declarations"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/QW-Group/qwprot"
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        source_dir = os.path.join(self.source_folder, "src")
        copy(
            self,
            "protocol.h",
            src=source_dir,
            dst=os.path.join(self.package_folder, "include", "qwprot"),
        )
        copy(
            self,
            "protocol.h",
            src=source_dir,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "qwprot")
        self.cpp_info.set_property("cmake_target_name", "qwprot::qwprot")
