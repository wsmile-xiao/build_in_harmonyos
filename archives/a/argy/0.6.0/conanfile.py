#!/usr/bin/env python3
"""Conan recipe — argy 0.6.0 (Header-only C++17 CLI argument parsing library).

argy 是零依赖、header-only 的 C++17 命令行参数解析库（含 argy.hpp 单头）。
无编译阶段；package 仅复制头文件与 LICENSE。test_package 实际 include
并调用 argy API（R34），上游测试见 MANIFEST.yml。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class ArgyConan(ConanFile):
    name = "argy"
    version = "0.6.0"
    description = "Argy: Command-Line Argument Parsing Library for Modern C++ (header-only, C++17)"
    license = "MIT"
    homepage = "https://github.com/mshenoda/argy"
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
        # header-only 库无编译阶段（R34：不伪造编译日志）
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
