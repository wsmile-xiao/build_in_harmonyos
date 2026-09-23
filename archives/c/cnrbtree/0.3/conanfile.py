#!/usr/bin/env python3
"""Conan recipe — cnrbtree 0.3 (single-header red-black tree library).

header-only: 上游仅 cnrbtree.h 一个头文件（#define CNRBTREE_IMPLEMENTATION
引入实现），Makefile 只用于构建上游测试/示例（testtree/simple）。
配方按本仓已验证的 header-only 模式（v12.21 conanfile-headeronly.py.tmpl
变体 A）实现：无编译产物，package() 直接拷贝头文件与 LICENSE，
test_package 真实 include 并调用公开 API（R34/R51 消费者验证）。
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class CnrbtreeConan(ConanFile):
    name = "cnrbtree"
    version = "0.3"
    description = "Fully-templated red black tree in C, usable as a dictionary or set (single-file header)"
    license = "MIT"
    homepage = "https://github.com/cnlohr/cnrbtree"
    url = ""  # CI fills this
    topics = ("red-black-tree", "dictionary", "set", "header-only", "c")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # 无编译阶段：build() 留空（header-only，无产物可编；不得伪造编译日志——R34）
    def build(self):
        apply_conandata_patches(self)

    def package(self):
        # 变体 A: header-only 库
        # 必须使用绝对 package_folder 目标：相对 dst 在 no_copy_source 布局下
        # 会落入 build 目录而非最终包目录（G2 实测教训）
        copy(self, "cnrbtree.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        # 变体 A: 标准头文件信息
        self.cpp_info.set_property("cmake_file_name", "cnrbtree")
        self.cpp_info.set_property("cmake_target_name", "cnrbtree::cnrbtree")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
