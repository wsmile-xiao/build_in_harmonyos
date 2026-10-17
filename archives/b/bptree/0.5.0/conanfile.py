#!/usr/bin/env python3
"""Conan recipe — bptree 0.5.0 (Header-only C library).

bptree 是单头文件 B+ tree C 库（include/bptree.h，BPTREE_IMPLEMENTATION
单头实现模式）：install 无编译产物，仅分发头文件。上游 Makefile 的
test/bench/example 目标针对开发者本地验证（clang -std=c11），不属于
库产物；本配方按 header-only 打包（R34: test_package 仍必须真实使用 API）。

package_type 用 "header-library"（Conan2 对纯头文件库的正确枚举，无需
shared option 且不产生 lib 产物）。copy() 的 src/dst 必须为绝对路径，
避免相对路径解析到 build 目录（boost-te 前例同款坑）。
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout

import os


class BptreeConan(ConanFile):
    name = "bptree"
    version = "0.5.0"
    description = "bptree 0.5.0 — single-header B+ tree implementation in C (habedi/bptree)"
    license = "MIT"
    homepage = "https://github.com/habedi/bptree"
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
        # header-only：仅应用 conandata 声明的补丁（当前 patches: {}，无补丁）
        apply_conandata_patches(self)

    def package(self):
        # header-only：分发 include/bptree.h（绝对路径 src/dst）
        copy(self, "bptree.h",
             os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"),
             keep_path=False)
        copy(self, "LICENSE*", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []