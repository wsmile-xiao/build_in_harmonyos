#!/usr/bin/env python3
"""Conan recipe — tinyformat 2.3.0 (header-only C++ formatting library).

tinyformat 是单头文件（tinyformat.h）的类型安全 printf 风格格式化库
（c42f/tinyformat），header-only：无编译产物、无第三方依赖。
上游仅用 CMakeLists/Makefile 构建测试（tinyformat_test / speed_test）。
铁律对齐: R34（test_package 真实 include 并调用 tfm::format 接口）；
R51（上游测试三步法照常适用，tinyformat_test 双变体已实测，台账见
notes.md / TEST_LEDGER）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class TinyformatConan(ConanFile):
    name = "tinyformat"
    version = "2.3.0"
    description = "Minimal, type safe printf() replacement library in a single C++ header file"
    license = "BSL-1.0"
    homepage = "https://github.com/c42f/tinyformat"
    url = ""  # CI fills this
    topics = ("format", "printf", "header-only", "cpp", "ostream")

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
        # 头文件位于源码根目录（单头文件），复制到 include/。
        copy(self, "tinyformat.h",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"),
             keep_path=False)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "tinyformat")
        self.cpp_info.set_property("cmake_target_name", "tinyformat::tinyformat")
        self.cpp_info.set_property("cmake_find_mode", "both")
