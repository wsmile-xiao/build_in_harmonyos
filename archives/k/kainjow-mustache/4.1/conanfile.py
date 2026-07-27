#!/usr/bin/env python3
"""Conan recipe — kainjow-mustache 4.1 (header-only)."""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class KainjowMustacheConan(ConanFile):
    name = "kainjow-mustache"
    version = "4.1"
    description = "Header-only Mustache implementation for modern C++"
    license = "BSL-1.0"
    homepage = "https://github.com/kainjow/Mustache"
    url = "https://github.com/kainjow/Mustache"
    topics = ("mustache", "template", "header-only")
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="kainjow-mustache-4.1.tar.gz",
            strip_root=True,
        )

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "mustache.hpp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "kainjow-mustache")
        self.cpp_info.set_property(
            "cmake_target_name", "kainjow-mustache::kainjow-mustache"
        )
        self.cpp_info.set_property("pkg_config_name", "kainjow-mustache")
