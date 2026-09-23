#!/usr/bin/env python3
"""Conan recipe — boost-te 1.0.0 (header-only).

[Boost].TE is a C++17 single-header type erasure library (include/boost/te.hpp).
Header-only: no build step; package() copies the header tree (R34: test_package
exercises the real API). Upstream CMakeLists.txt defines no install() rule
(only examples + tests), so headers are copied directly.
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

import os


class BoostteConan(ConanFile):
    name = "boost-te"
    version = "1.0.0"
    description = "[Boost].TE: C++17 Type Erasure library (header-only, boost-ext/te)"
    license = "BSL-1.0"
    homepage = "https://github.com/boost-ext/te"
    url = "https://github.com/boost-ext/te"

    package_type = "header-library"

    # 无编译产物 → settings 仅保留结构一致性；package_id 清空见下
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
        # header-only：分发 include/boost/ 全部头文件（仅 te.hpp）
        # 注意：copy() 的 src/dst 必须为绝对路径，避免相对路径解析到 build 目录
        copy(self, "boost/*", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        # 标准头文件信息
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
