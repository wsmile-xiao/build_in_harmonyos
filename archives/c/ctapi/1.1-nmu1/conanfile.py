#!/usr/bin/env python3
"""Conan recipe — ctapi 1.1-nmu1 (header-only C API)."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
)
from conan.tools.layout import basic_layout


class CtapiConan(ConanFile):
    name = "ctapi"
    version = "1.1-nmu1"
    package_type = "header-library"

    description = "Card Terminal API 1.1 interface definition"
    license = "Public-Domain"
    homepage = "https://tracker.debian.org/pkg/ctapi"
    url = "https://tracker.debian.org/pkg/ctapi"
    topics = ("ct-api", "smart-card", "iso-7816")

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        source = self.conan_data["sources"]
        download(
            self,
            url=source["url"],
            filename="ctapi.h",
            sha256=source["sha256"],
        )

    def build(self):
        apply_conandata_patches(self)
        header = os.path.join(self.source_folder, "ctapi.h")
        if not os.path.isfile(header):
            raise RuntimeError("upstream ctapi.h was not downloaded")
        with open(header, encoding="utf-8") as source:
            contents = source.read()
        required_declarations = ("CT_init", "CT_data", "CT_close")
        if not all(name in contents for name in required_declarations):
            raise RuntimeError("upstream ctapi.h is missing a CT-API declaration")

    def package(self):
        copy(
            self,
            "ctapi.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "ctapi.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "ctapi")
        self.cpp_info.set_property("cmake_target_name", "ctapi::ctapi")
