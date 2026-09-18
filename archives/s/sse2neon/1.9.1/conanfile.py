#!/usr/bin/env python3
"""Conan recipe — sse2neon 1.9.1 (single-header SSE→NEON translation library).

header-only: 上游仅有 sse2neon.h 一个头文件（无编译/无安装产物），
Makefile 只用于运行上游测试。配方按本仓已验证的 header-only 模式
（v12.21 conanfile-headeronly.py.tmpl 变体 A）实现：无 build()，
package() 直接拷贝头文件与 LICENSE，test_package 真实 include 并调用
公开 SIMD API（R34/R51）。
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class Sse2NeonConan(ConanFile):
    name = "sse2neon"
    version = "1.9.1"
    description = "A translator from Intel SIMD intrinsics to ARM/AArch64 NEON"
    license = "MIT"
    homepage = "https://github.com/DLTcollab/sse2neon"
    url = ""  # CI fills this
    topics = ("simd", "neon", "sse", "header-only", "arm")

    package_type = "header-library"

    # 无编译产物 → settings 仅保留结构一致性；package_id 清空见 package_id()
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
        copy(self, "sse2neon.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        # 变体 A: 标准头文件信息
        self.cpp_info.set_property("cmake_file_name", "sse2neon")
        self.cpp_info.set_property("cmake_target_name", "sse2neon::sse2neon")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
