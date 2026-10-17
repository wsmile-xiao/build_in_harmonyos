#!/usr/bin/env python3
"""Conan recipe for the jane-street-headers 0.17.0 C header files."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class JaneStreetHeadersConan(ConanFile):
    name = "jane-street-headers"
    version = "0.17.0"
    package_type = "header-library"

    description = "C header files shared between the various Jane Street packages"
    license = "MIT"
    homepage = "https://github.com/janestreet/jane-street-headers"
    url = "https://github.com/janestreet/jane-street-headers"
    topics = ("janestreet", "ocaml", "headers")

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
            "LICENSE.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "jane-street-headers")
        self.cpp_info.set_property(
            "cmake_target_name", "jane-street-headers::jane-street-headers"
        )
