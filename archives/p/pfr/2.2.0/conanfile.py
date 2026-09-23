#!/usr/bin/env python3
"""Conan recipe for Boost.PFR 2.2.0, a header-only reflection library."""
import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class PfrConan(ConanFile):
    name = "pfr"
    version = "2.2.0"
    description = "Header-only C++14 reflection utilities for aggregate types"
    license = "BSL-1.0"
    homepage = "https://github.com/boostorg/pfr"
    url = "https://github.com/boostorg/pfr"
    topics = ("boost", "pfr", "reflection", "header-only")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        cppstd = self.settings.compiler.get_safe("cppstd")
        if cppstd:
            check_min_cppstd(self, "14")

    def build(self):
        # The upstream project is an INTERFACE target. Keep the no-op patch
        # hook explicit so the recipe remains compatible with conandata patches.
        apply_conandata_patches(self)
        self.output.info("Boost.PFR is header-only; no compiled package target is built")

    def package(self):
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=True,
        )
        copy(
            self,
            "LICENSE_1_0.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "pfr")
        self.cpp_info.set_property("cmake_target_name", "boost::pfr")
        self.cpp_info.set_property("pkg_config_name", "pfr")
