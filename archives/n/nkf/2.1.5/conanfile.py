#!/usr/bin/env python3
"""Conan recipe — nkf 2.1.5 (Makefile)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class NkfConan(ConanFile):
    name = "nkf"
    version = "2.1.5"
    description = "Network Kanji Filter — a Japanese text encoding converter"
    license = "MIT"
    homepage = "https://github.com/nurse/nkf"
    url = homepage

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R9: Use -j1, never -j$(nproc)
        # R33: Hardcode compiler, never use ${CC} shell variable
        self.run('make CC=clang CFLAGS="-fPIC -O2 -Wall" MKDIR="mkdir -p" -j1',
                 cwd=self.source_folder)

    def package(self):
        copy(self, "nkf", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "nkf.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "nkf.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "utf8tbl.h", self.source_folder, os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
