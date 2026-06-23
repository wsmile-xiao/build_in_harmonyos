#!/usr/bin/env python3
"""Conan recipe template — Makefile projects (raw make, no configure).

Usage: Replace P7Zip, 7zip, 23.01, 高压缩比文件归档工具，支持 7z、ZIP、GZIP 等多种格式, LGPL-2.1, https://www.7-zip.org
       Fill in requires(), build commands, and cpp_info.libs as needed.

Makefile projects typically build static libs by default (e.g. bzip2).
Do NOT build shared variants (R26).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class P7ZipConan(ConanFile):
    name = "7zip"
    version = "23.01"
    description = "高压缩比文件归档工具，支持 7z、ZIP、GZIP 等多种格式"
    license = "LGPL-2.1"
    homepage = "https://www.7-zip.org"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R26: Only build static targets, do NOT build shared variants
        # Adjust CC/AR/RANLIB as needed for the toolchain
        self.run("make CC=clang AR=llvm-ar RANLIB=llvm-ranlib -j$(nproc)")
        # Do NOT run: make -f Makefile-libbz2_so  (that builds shared lib)

    def package(self):
        copy(self, "*.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "*.a", self.source_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "7zip", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["7zip"]
