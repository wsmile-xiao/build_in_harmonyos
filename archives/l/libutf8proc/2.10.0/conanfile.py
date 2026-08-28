#!/usr/bin/env python3
"""Conan recipe — libutf8proc 2.10.0 (UTF-8 processing library).

Build system: upstream Makefile (also ships CMakeLists.txt; this recipe uses Makefile).
No external dependencies. Bootstrap skeleton — build/package 逻辑在 adapt 阶段填充验证。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Libutf8procConan(ConanFile):
    name = "libutf8proc"
    version = "2.10.0"
    description = "A clean C library for processing UTF-8 Unicode data"
    license = "MIT"
    homepage = "https://github.com/JuliaStrings/utf8proc"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # 上游 Makefile 构建 libutf8proc.a / libutf8proc.so
        self.run("make -j1", cwd=self.source_folder)
        if self.options.shared:
            self.run("make -j1 libutf8proc.$(SHLIB_VERS_EXT)", cwd=self.source_folder)

    def package(self):
        # 头文件
        copy(self, "utf8proc.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        # 静态库
        copy(self, "libutf8proc.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        if self.options.shared:
            copy(self, "libutf8proc.so*", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["utf8proc"]
