#!/usr/bin/env python3
"""Conan recipe — brickworks 1.4.3 (header-only music DSP toolkit).

brickworks is a header-only C library: all functionality lives in
include/bw_*.h (59 headers), no `.c` sources outside test/.  Adapt as
variant A (Header-only) per templates/conanfile-headeronly.py.tmpl.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BrickworksConan(ConanFile):
    name = "brickworks"
    version = "1.4.3"
    description = "Brickworks music DSP toolkit (header-only)"
    license = "GPL-3.0"
    homepage = "https://www.orastron.com/algorithms#brickworks"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only: no compilation; only apply declared patches (none).
        apply_conandata_patches(self)

    def package(self):
        # 显式使用 package_folder 绝对路径：相对 dst 会被解析到 build 目录。
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # header-only -> single package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []