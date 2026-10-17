#!/usr/bin/env python3
"""Conan recipe for csv-parser 1.1 — header-only C++17 CSV parsing library.

csv-parser is a modern C++ header-only library (MIT) requiring C++17.
No build step needed; package() copies *.hpp headers to include/.
"""
from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class CsvParserConan(ConanFile):
    name = "csv-parser"
    version = "1.1"
    description = "CSV parser for Modern C++ - header-only library"
    license = "MIT"
    homepage = "https://github.com/p-ranav/csv"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("csv", "parser", "header-only")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        copy(
            self,
            pattern="*.hpp",
            dst=os.path.join(self.package_folder, "include"),
            src=os.path.join(self.source_folder, "include"),
        )

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
