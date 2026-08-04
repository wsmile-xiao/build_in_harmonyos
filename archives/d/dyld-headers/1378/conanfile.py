#!/usr/bin/env python3
"""Conan recipe for the dyld 1378 public headers."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class DyldHeadersConan(ConanFile):
    name = "dyld-headers"
    version = "1378"
    package_type = "header-library"

    description = "Header files for the Apple dynamic linker"
    license = "APSL-2.0"
    homepage = "https://github.com/apple-oss-distributions/dyld"
    url = "https://github.com/apple-oss-distributions/dyld"
    topics = ("dyld", "mach-o", "headers")

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        include_dir = os.path.join(self.source_folder, "include")
        if not os.path.isdir(include_dir):
            raise RuntimeError("upstream include directory was not found")

    def package(self):
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "APPLE_LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "dyld-headers")
        self.cpp_info.set_property(
            "cmake_target_name", "dyld-headers::dyld-headers"
        )
