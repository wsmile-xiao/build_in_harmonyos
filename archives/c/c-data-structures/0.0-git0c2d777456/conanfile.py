#!/usr/bin/env python3
"""Conan recipe for c-data-structures 0.0-git0c2d777456 — header-only C library.

Upstream (https://github.com/schellingb/c-data-structures) is a set of
single-file public-domain C data structure headers (tinybuf.h dynamic
array, tinyhashmap.h / tinyhashmap64.h hash maps).  There is no build
system and no compiled artifact: this recipe packages the headers only
(header-only variant A, template conanfile-headeronly.py.tmpl).

R34: test_package real consumer — test.c includes every public header
and exercises the actual macro APIs with observable results.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy
from conan.tools.layout import basic_layout


class CDataStructuresConan(ConanFile):
    name = "c-data-structures"
    version = "0.0-git0c2d777456"
    description = ("Simple and convenient single-file public domain C/C++ data "
                   "structures: TinyHashMap (32/64-bit keys) and TinyBuf dynamic array")
    license = "Unlicense"
    homepage = "https://github.com/schellingb/c-data-structures"
    url = "https://github.com/schellingb/c-data-structures"

    package_type = "header-library"

    # No compiled artifact → settings kept for structure consistency only.
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "UNLICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # header-only: single package_id

    def package_info(self):
        # Header-only: no libs/bins.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
