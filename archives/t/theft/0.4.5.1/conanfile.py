#!/usr/bin/env python3
"""Conan recipe for the theft C property-based testing library (Makefile)."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class TheftConan(ConanFile):
    name = "theft"
    version = "0.4.5.1"
    description = "Property-based testing framework for C"
    license = "ISC"
    homepage = "https://github.com/silentbicycle/theft"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        self.settings.rm_safe("os.version")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "ar")
        ranlib = compilers.get("ranlib", "ranlib")
        make_cmd = f'make CC="{cc}" AR="{ar}" RANLIB="{ranlib}" -j1'
        if can_run(self):
            self.run(make_cmd + " all test", cwd=self.source_folder)
        else:
            self.run(make_cmd + " all", cwd=self.source_folder)

    def package(self):
        copy(self, "theft*.h", src=os.path.join(self.source_folder, "inc"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libtheft.a", src=os.path.join(self.source_folder, "build"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["theft"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "theft")
        self.cpp_info.set_property("cmake_target_name", "theft::theft")
