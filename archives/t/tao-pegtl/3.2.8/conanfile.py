#!/usr/bin/env python3
"""Conan recipe — tao-pegtl 3.2.8 header-only (变体 A).

tao-pegtl (PEGTL, Parsing Expression Grammar Template Library) 是纯头文件
C++17 库：src/ 下无库源码（仅 example/test），无编译产物。
铁律对齐: R34（test_package 真实 include 并调用 pegtl 接口）；R51（上游
测试三步法照常适用，128 项 ctest 已在 notes.md 申报并实测）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class TaopegtlConan(ConanFile):
    name = "tao-pegtl"
    version = "3.2.8"
    description = "PEGTL: Parsing Expression Grammar Template Library, a header-only C++17 parser combinator library"
    license = "MIT"
    homepage = "https://github.com/taocpp/PEGTL"
    url = ""  # CI fills this

    package_type = "header-library"

    # 无编译产物 → settings 仅保留结构一致性；package_id 清空见下
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only：无编译阶段。apply_conandata_patches 保持配方接口一致
        # （当前 patches: {} 为空，本方法不产生任何编译日志——R34）
        apply_conandata_patches(self)

    def package(self):
        # 头文件位于 include/tao/**（嵌套），从 include 目录整体递归复制。
        # dst 必须是 package_folder 下绝对路径，否则复制到错误目录
        copy(self, "*",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=True)
        copy(self, "LICENSE*", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "tao-pegtl")
        self.cpp_info.set_property("cmake_target_name", "tao-pegtl::tao-pegtl")
        self.cpp_info.set_property("cmake_find_mode", "both")