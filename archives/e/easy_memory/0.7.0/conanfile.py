#!/usr/bin/env python3
"""Conan recipe — easy_memory 0.7.0 (header-only C 库, MIT)

上游: https://github.com/EasyMem/easy_memory
单头文件分配器 (easy_memory.h), 无编译产物, package 仅分发头文件。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class EasymemoryConan(ConanFile):
    name = "easy_memory"
    version = "0.7.0"
    description = "A strictly typed, platform-agnostic, safe memory management system for C (header-only)"
    license = "MIT"
    homepage = "https://github.com/EasyMem/easy_memory"
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
        # header-only: 无编译步骤; 仅应用补丁 (若有)
        apply_conandata_patches(self)

    def package(self):
        # 仅打包公共头文件（easy_memory.h）; fuzzers/tests 辅助头不入包
        copy(self, "easy_memory.h", src=self.source_folder,
             dst=self.package_folder, keep_path=False)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["."]