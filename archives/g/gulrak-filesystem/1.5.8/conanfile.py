#!/usr/bin/env python3
"""Conan recipe — gulrak-filesystem 1.5.8 (header-only, ghc::filesystem).

上游项目 gulrak/filesystem 是单头/多文件 header-only 的 std::filesystem
fallback 实现（include/ghc/*.hpp）。无编译阶段，package 只搬运头文件
与 LICENSE；test_package 以真实代码 include 并调用其 API（R34）。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class GulrakFilesystemConan(ConanFile):
    name = "gulrak-filesystem"
    version = "1.5.8"
    description = "gulrak-filesystem: A cross-platform C++ filesystem library, based on the C++17 std::filesystem reference implementation"
    license = "MIT"
    homepage = "https://github.com/gulrak/filesystem"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        # 保留相对路径复制 include/ghc/*.hpp → package include/ghc/*.hpp
        copy(self, "ghc/*.hpp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()  # header-only：无构建依赖 → 单一 package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []