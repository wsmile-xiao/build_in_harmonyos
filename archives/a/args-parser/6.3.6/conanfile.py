#!/usr/bin/env python3
"""Conan recipe — args-parser 6.3.6 (header-only CMake library)"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import cmake_layout


class ArgsParserConan(ConanFile):
    name = "args-parser"
    version = "6.3.6"
    description = "C++ command line arguments parser (header-only)"
    license = "MIT"
    homepage = "https://github.com/igormironchik/args-parser"
    url = ""  # CI fills this
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def build(self):
        # header-only: no compile step
        apply_conandata_patches(self)

    def package(self):
        copy(
            self,
            "*.hpp",
            src=self.source_folder,
            dst=self.package_folder,
        )
        copy(
            self,
            "*.h",
            src=self.source_folder,
            dst=self.package_folder,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["."]
