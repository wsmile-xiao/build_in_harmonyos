#!/usr/bin/env python3
"""Conan recipe — minilua 5.4.7 (single-header Lua 5.4.7 library)."""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MiniluaConan(ConanFile):
    name = "minilua"
    version = "5.4.7"
    description = "Single-header port of Lua 5.4.7"
    license = "MIT"
    homepage = "https://github.com/edubart/minilua"
    url = "https://github.com/edubart/minilua"

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        self.info.clear()

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # minilua is distributed as a generated single header; there is no
        # library target to build. Keep the patch hook for recipe consistency.
        apply_conandata_patches(self)

    def package(self):
        copy(self, "minilua.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "minilua")
        self.cpp_info.set_property("cmake_target_name", "minilua")
