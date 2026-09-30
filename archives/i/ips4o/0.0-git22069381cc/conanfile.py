#!/usr/bin/env python3
"""Conan recipe — ips4o 0.0-git22069381cc (header-only, 无构建打包族).

ips4o (In-place Parallel Super Scalar Samplesort) 是 header-only C++14 排序库。
本 commit 上游无构建系统（无 CMake/Makefile）、无测试目录、无样例与基准，
因此配方只安装头文件，并由 test_package 实际包含并调用公开 API 验真（R34）。
并行排序需要 OpenMP（-fopenmp）或 std::thread，属消费者编译期选择，
配方不引入额外依赖（依赖解析确认 0 依赖）。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class Ips4OConan(ConanFile):
    name = "ips4o"
    version = "0.0-git22069381cc"
    description = "In-place Parallel Super Scalar Samplesort (IPS4o) header-only sorting library"
    license = "BSD-2-Clause"
    homepage = "https://github.com/vgteam/ips4o"
    url = "https://github.com/vgteam/ips4o"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only：无编译阶段；保留补丁应用调用（patches 为空时为 no-op），
        # 不伪造任何编译产物（R34）。
        apply_conandata_patches(self)

    def package(self):
        # 变体 A: header-only — 保留 ips4o/ 子目录相对路径，顶层 ips4o.hpp 不变
        copy(self, "*.hpp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # 无编译依赖 → 单一 package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []