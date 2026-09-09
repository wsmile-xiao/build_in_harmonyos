#!/usr/bin/env python3
"""Conan recipe — rtm 2.3.1 (Realtime Math, header-only C++).

rtm 是 Nicholas Frechette 的 Realtime Math 库：SIMD 优化的标量/向量/矩阵/
四元数等数学类型，纯 header-only（includes/rtm，62 个头文件，无编译产物）。
变体 A（header-only 库）：只安装头文件 + LICENSE，无 build()。
对齐铁律：R34（test_package 实际 include 并使用矢量/矩阵 API）、
R51（上游测试三步法：tests/main_generic + Catch2 ctest 已清点并实测）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RtmConan(ConanFile):
    name = "rtm"
    version = "2.3.1"
    description = "Realtime Math (rtm) - SIMD optimized vector, matrix and quaternion math library, header-only"
    license = "MIT"
    homepage = "https://github.com/nfrechette/rtm"
    url = "https://github.com/nfrechette/rtm"

    package_type = "header-library"

    # 无编译产物 → settings 仅保留结构一致性；package_id 清空实现单一包
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # 无编译阶段：header-only 库不产生编译产物，build() 留空（不伪造编译日志 — R34）
    def build(self):
        pass

    def package(self):
        # ── 变体 A: header-only 库（rtm 头文件位于 includes/rtm/**，保留目录结构）──
        # 注意: dst 必须基于 self.package_folder 的绝对路径，否则相对路径会被
        # 解析到 build 目录（实测教训）→ include 落空。
        pkg_include = os.path.join(self.package_folder, "include")
        pkg_licenses = os.path.join(self.package_folder, "licenses")
        copy(self, "*.h", src=os.path.join(self.source_folder, "includes"),
             dst=pkg_include)
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "includes"),
             dst=pkg_include)
        copy(self, "*.inl", src=os.path.join(self.source_folder, "includes"),
             dst=pkg_include)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=pkg_licenses, keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        # 变体 A: 标准头文件信息
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []