#!/usr/bin/env python3
"""Conan recipe — lzav 5.17 (header-only C/C++ data compression library).

LZAV is a fast, portable, scalar, header-only lossless in-memory compression
algorithm (LZ77-based). One header file `lzav.h` provides the whole library;
it conforms to ISO C99 and is C++ compatible.
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import cmake_layout


class LzavConan(ConanFile):
    name = "lzav"
    version = "5.17"
    description = "LZAV - Fast In-memory Data Compression Algorithm (header-only, C99/C++)"
    license = "MIT"
    homepage = "https://github.com/avaneev/lzav"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only: no compilation step. Patches (if any) are applied
        # here, keeping the recipe complete for CI (R34 — the consumer test
        # in test_package/ really includes lzav.h and exercises the API).
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.h", src=self.source_folder, dst=self.package_folder)
        copy(self, "*.hpp", src=self.source_folder, dst=self.package_folder)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=("licenses" if self.package_folder else self.package_folder),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["."]